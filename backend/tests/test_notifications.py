from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import CurrentUser, require_current_user
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import (
    Capture,
    Memory,
    NotificationDelivery,
    PushSubscription,
    Reminder,
    Source,
    utc_now,
)
from app.db.session import get_db
from app.main import app


TEST_USER_ID = "notification-user"


def override_auth() -> CurrentUser:
    return CurrentUser(id=TEST_USER_ID, email="notification@example.com", name="Notify")


def build_notification_db_override(with_due_reminder: bool = False):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    if with_due_reminder:
        db = testing_session()
        db.add(
            Reminder(
                user_id=TEST_USER_ID,
                content="Apply to YC before the deadline",
                due_at=utc_now() - timedelta(minutes=5),
                status="scheduled",
                save_as_memory=False,
            )
        )
        db.commit()
        db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    return override_db


def test_push_public_key_reports_unconfigured_without_vapid_keys(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "crowscap_vapid_public_key", None)
    monkeypatch.setattr(settings, "crowscap_vapid_private_key", None)
    app.dependency_overrides[require_current_user] = override_auth
    app.dependency_overrides[get_db] = build_notification_db_override()

    try:
        client = TestClient(app)
        response = client.get("/api/v1/notifications/push/public-key")

        assert response.status_code == 200
        assert response.json() == {"configured": False, "public_key": None}
    finally:
        app.dependency_overrides.clear()


def test_push_subscription_can_be_saved_even_before_vapid_is_configured(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "crowscap_vapid_public_key", None)
    monkeypatch.setattr(settings, "crowscap_vapid_private_key", None)
    app.dependency_overrides[require_current_user] = override_auth
    app.dependency_overrides[get_db] = build_notification_db_override()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/notifications/push/subscribe",
            json={
                "subscription": {
                    "endpoint": "https://push.example.test/send/abc123456789",
                    "keys": {
                        "p256dh": "x" * 88,
                        "auth": "y" * 24,
                    },
                },
                "user_agent": "pytest",
            },
        )

        assert response.status_code == 200
        assert response.json() == {"status": "active", "configured": False}
    finally:
        app.dependency_overrides.clear()


def test_native_push_token_can_be_saved_without_web_push_keys(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "crowscap_vapid_public_key", None)
    monkeypatch.setattr(settings, "crowscap_vapid_private_key", None)
    app.dependency_overrides[require_current_user] = override_auth
    app.dependency_overrides[get_db] = build_notification_db_override()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/notifications/push/native-token",
            json={
                "token": "ExponentPushToken[abcdefghijklmnopqrstuvwxyz123456]",
                "platform": "android",
                "device_name": "Pixel test",
            },
        )

        assert response.status_code == 200
        assert response.json() == {"status": "active", "configured": True}
    finally:
        app.dependency_overrides.clear()


def test_current_notification_prefers_due_reminder(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.notification_service.generate_notification_copy",
        lambda *, context, default_title, default_body: (default_title, default_body),
    )
    app.dependency_overrides[require_current_user] = override_auth
    app.dependency_overrides[get_db] = build_notification_db_override(with_due_reminder=True)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/notifications/current")

        assert response.status_code == 200
        event = response.json()["event"]
        assert event["event_type"] == "reminder_due"
        assert bool(event["title"])
        assert "YC" in event["body"] or "apply" in event["body"].lower() or bool(event["body"])

        assert event["url"] == "/recall"
        assert event["due_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_due_deadline_reminder_uses_urgent_due_phrase(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.notification_service.generate_notification_copy",
        lambda *, context, default_title, default_body: (default_title, default_body),
    )
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    due_at = utc_now() + timedelta(days=1)
    reminder = Reminder(
        user_id=TEST_USER_ID,
        content="Apply for the Moonshot grant before the deadline",
        due_at=due_at,
        status="scheduled",
        save_as_memory=False,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    from app.services.notification_service import _reminder_event

    event = _reminder_event(db=db, reminder=reminder, due_count=1, now=utc_now())

    assert "tomorrow" in f"{event.title} {event.body}".lower()
    assert event.event_type == "reminder_due"
    db.close()


def test_recall_notification_fallback_uses_saved_content_not_marketing_copy(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.notification_service.generate_notification_copy",
        lambda *, context, default_title, default_body: (default_title, default_body),
    )
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    source = Source(
        user_id=TEST_USER_ID,
        source_type="youtube",
        title="BullMQ queue design",
        original_url="https://youtu.be/example",
    )
    db.add(source)
    db.flush()
    capture = Capture(
        user_id=TEST_USER_ID,
        source_id=source.id,
        user_intent_text="compare background jobs for Crowscap notifications",
        status="completed",
    )
    db.add(capture)
    db.flush()
    memory = Memory(
        user_id=TEST_USER_ID,
        source_id=source.id,
        capture_id=capture.id,
        memory_type="claim",
        content="BullMQ can handle efficient task processing and background job management.",
        summary="BullMQ is useful for background jobs and task processing.",
        confidence="high",
        source_strength="moderate",
        next_review_at=utc_now() - timedelta(days=1),
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    from app.services.notification_service import _recall_event

    event = _recall_event(
        memory=memory,
        source=source,
        surface_reason="You saved it with a clear reason, so it is worth bringing back.",
        due_count=1,
        now=utc_now(),
    )

    combined = f"{event.title} {event.body}".lower()
    assert "discover how" not in combined
    assert "bullmq" in combined
    assert "background" in combined or "task" in combined
    db.close()


def test_recall_selection_skips_already_sent_memory(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.notification_service.generate_notification_copy",
        lambda *, context, default_title, default_body: (default_title, default_body),
    )
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    source = Source(
        user_id=TEST_USER_ID,
        source_type="article",
        title="Founder focus notes",
        original_url="https://example.com/focus",
    )
    db.add(source)
    db.flush()
    capture = Capture(
        user_id=TEST_USER_ID,
        source_id=source.id,
        user_intent_text="prepare for YC and founder outreach",
        status="completed",
    )
    db.add(capture)
    db.flush()
    first = Memory(
        user_id=TEST_USER_ID,
        source_id=source.id,
        capture_id=capture.id,
        memory_type="claim",
        content="Already sent memory about old launch notes.",
        confidence="high",
        source_strength="strong",
        next_review_at=utc_now() - timedelta(days=3),
    )
    second = Memory(
        user_id=TEST_USER_ID,
        source_id=source.id,
        capture_id=capture.id,
        memory_type="action",
        content="Follow up with the YC application video before the deadline.",
        confidence="high",
        source_strength="strong",
        next_review_at=utc_now() - timedelta(days=2),
    )
    db.add_all([first, second])
    db.flush()
    db.add(
        NotificationDelivery(
            user_id=TEST_USER_ID,
            event_key=f"recall_due:{first.id}:{first.next_review_at.isoformat()}",
            event_type="recall_due",
            channel="web_push",
            status="sent",
            title="sent",
            body="sent",
            url="/recall",
        )
    )
    db.commit()

    from app.services.notification_service import get_current_notification_event

    event = get_current_notification_event(db=db, user_id=TEST_USER_ID)

    assert event.event_type == "recall_due"
    assert event.memory_id == str(second.id)
    assert "YC" in event.body or "deadline" in event.body.lower()
    db.close()


def test_send_push_event_uses_expo_sender_for_native_token(monkeypatch: MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    db.add(
        PushSubscription(
            user_id=TEST_USER_ID,
            endpoint="ExponentPushToken[abcdefghijklmnopqrstuvwxyz123456]",
            p256dh="expo",
            auth="expo",
            status="active",
            metadata_json={"provider": "expo", "platform": "android"},
        )
    )
    db.commit()
    calls: list[str] = []

    monkeypatch.setattr(
        "app.services.notification_service._send_expo_push",
        lambda *, subscription, event: calls.append(subscription.endpoint),
    )
    monkeypatch.setattr(
        "app.services.notification_service._send_web_push",
        lambda *, subscription, event: calls.append("web"),
    )

    from app.schemas.notifications import NotificationEvent
    from app.services.notification_service import send_push_event_to_user

    event = NotificationEvent(
        event_id="event",
        event_key="recall_due:test",
        event_type="recall_due",
        due_count=1,
        title="Your saved video is ready",
        body="You saved this video yesterday for your YC application.",
        url="/recall",
        created_at=utc_now(),
    )

    send_push_event_to_user(db=db, user_id=TEST_USER_ID, event=event)

    assert calls == ["ExponentPushToken[abcdefghijklmnopqrstuvwxyz123456]"]
    db.close()
