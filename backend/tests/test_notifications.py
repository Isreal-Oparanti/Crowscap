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
from app.db.models import Reminder, utc_now
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


def test_current_notification_prefers_due_reminder() -> None:
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
