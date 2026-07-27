from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    Memory,
    NotificationDelivery,
    PushSubscription,
    Reminder,
    utc_now,
)
from app.db.session import SessionLocal
from app.schemas.notifications import (
    NotificationEvent,
    PushSubscriptionPayload,
)

logger = get_logger("services.notification")

try:
    from pywebpush import WebPushException, webpush
except Exception:  # pragma: no cover - import depends on optional runtime package
    WebPushException = Exception  # type: ignore[assignment]
    webpush = None  # type: ignore[assignment]


def get_push_public_key() -> tuple[bool, str | None]:
    settings = get_settings()
    configured = settings.push_notifications_configured
    return configured, settings.crowscap_vapid_public_key if configured else None


def upsert_push_subscription(
    *,
    db: Session,
    user_id: str,
    payload: PushSubscriptionPayload,
    user_agent: str | None,
) -> PushSubscription:
    existing = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint)
    )
    if existing is None:
        existing = PushSubscription(
            user_id=user_id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
        )
        db.add(existing)

    existing.user_id = user_id
    existing.p256dh = payload.keys.p256dh
    existing.auth = payload.keys.auth
    existing.status = "active"
    existing.user_agent = user_agent
    existing.last_seen_at = utc_now()
    existing.last_error = None
    db.commit()
    db.refresh(existing)
    return existing


def deactivate_push_subscription(
    *,
    db: Session,
    user_id: str,
    endpoint: str,
    reason: str = "user_unsubscribed",
) -> bool:
    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    if subscription is None:
        return False
    subscription.status = "disabled"
    subscription.last_error = reason
    db.commit()
    return True


def get_current_notification_event(*, db: Session, user_id: str) -> NotificationEvent:
    now = utc_now()

    due_reminder = db.scalar(
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.status == "scheduled",
            Reminder.due_at <= now,
        )
        .order_by(Reminder.due_at.asc())
        .limit(1)
    )
    reminder_count = db.scalar(
        select(func.count(Reminder.id)).where(
            Reminder.user_id == user_id,
            Reminder.status == "scheduled",
            Reminder.due_at <= now,
        )
    ) or 0

    due_memory = db.scalar(
        select(Memory)
        .where(
            Memory.user_id == user_id,
            Memory.status == "active",
            Memory.next_review_at.is_not(None),
            Memory.next_review_at <= now,
        )
        .order_by(Memory.next_review_at.asc())
        .limit(1)
    )
    memory_count = db.scalar(
        select(func.count(Memory.id)).where(
            Memory.user_id == user_id,
            Memory.status == "active",
            Memory.next_review_at.is_not(None),
            Memory.next_review_at <= now,
        )
    ) or 0

    if due_reminder is not None:
        return _reminder_event(
            reminder=due_reminder,
            due_count=int(reminder_count) + int(memory_count),
            now=now,
        )
    if due_memory is not None:
        return _recall_event(
            memory=due_memory,
            due_count=int(reminder_count) + int(memory_count),
            now=now,
        )
    return NotificationEvent(
        event_id=str(uuid.uuid4()),
        event_key=f"heartbeat:{user_id}",
        event_type="heartbeat",
        due_count=0,
        title="Crowscap is listening",
        body="No reminders or recalls are due right now.",
        url="/",
        created_at=now,
    )


def send_due_pushes_once(*, db: Session, user_id: str) -> NotificationEvent:
    event = get_current_notification_event(db=db, user_id=user_id)
    if event.event_type == "heartbeat":
        return event
    send_push_event_to_user(db=db, user_id=user_id, event=event)
    return event


def send_push_event_to_user(
    *,
    db: Session,
    user_id: str,
    event: NotificationEvent,
) -> None:
    settings = get_settings()
    if not settings.push_notifications_configured:
        logger.info("notification.push.skipped reason=vapid_not_configured user_id=%s", user_id)
        return
    if webpush is None:
        logger.warning("notification.push.skipped reason=pywebpush_missing user_id=%s", user_id)
        return

    delivery = db.scalar(
        select(NotificationDelivery).where(
            NotificationDelivery.event_key == event.event_key,
            NotificationDelivery.channel == "web_push",
        )
    )
    if delivery is not None and delivery.status == "sent":
        return
    if delivery is None:
        delivery = NotificationDelivery(
            user_id=user_id,
            event_key=event.event_key,
            event_type=event.event_type,
            channel="web_push",
            status="pending",
            title=event.title,
            body=event.body,
            url=event.url,
            attempts=0,
            metadata_json={
                "reminder_id": event.reminder_id,
                "memory_id": event.memory_id,
            },
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)

    subscriptions = db.scalars(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.status == "active",
        )
    ).all()
    if not subscriptions:
        delivery.status = "skipped"
        delivery.error_message_safe = "No active push subscriptions."
        delivery.attempts += 1
        db.commit()
        return

    sent_any = False
    last_error: str | None = None
    for subscription in subscriptions:
        try:
            _send_web_push(subscription=subscription, event=event)
            sent_any = True
            subscription.last_error = None
            subscription.last_seen_at = utc_now()
        except WebPushException as exc:
            last_error = _safe_push_error(exc)
            subscription.last_error = last_error
            if _is_expired_subscription(exc):
                subscription.status = "disabled"
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            last_error = _safe_push_error(exc)
            subscription.last_error = last_error

    delivery.attempts += 1
    if sent_any:
        delivery.status = "sent"
        delivery.sent_at = utc_now()
        delivery.error_message_safe = None
    else:
        delivery.status = "failed"
        delivery.error_message_safe = last_error or "Push delivery failed."
    db.commit()


async def notification_worker_loop(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    interval = max(15.0, settings.crowscap_notification_worker_interval_seconds)
    logger.info("notification.worker.start interval=%s", interval)

    while not stop_event.is_set():
        try:
            await asyncio.to_thread(_deliver_due_notifications_for_all_users)
        except Exception as exc:  # pragma: no cover - long-running process guard
            logger.exception(
                "notification.worker.error error_type=%s",
                type(exc).__name__,
            )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue

    logger.info("notification.worker.stop")


def _deliver_due_notifications_for_all_users() -> None:
    with SessionLocal() as db:
        user_ids = db.scalars(
            select(PushSubscription.user_id)
            .where(PushSubscription.status == "active")
            .distinct()
        ).all()
        for user_id in [item for item in user_ids if item]:
            send_due_pushes_once(db=db, user_id=user_id)


def _reminder_event(
    *,
    reminder: Reminder,
    due_count: int,
    now: datetime,
) -> NotificationEvent:
    return NotificationEvent(
        event_id=str(uuid.uuid4()),
        event_key=f"reminder_due:{reminder.id}:{reminder.due_at.isoformat()}",
        event_type="reminder_due",
        due_count=due_count,
        title="Reminder ready",
        body=_clip(reminder.content, 140),
        url="/recall",
        reminder_id=reminder.id,
        created_at=now,
    )


def _recall_event(
    *,
    memory: Memory,
    due_count: int,
    now: datetime,
) -> NotificationEvent:
    return NotificationEvent(
        event_id=str(uuid.uuid4()),
        event_key=f"recall_due:{memory.id}:{memory.next_review_at.isoformat() if memory.next_review_at else 'due'}",
        event_type="recall_due",
        due_count=due_count,
        title="A thought is ready",
        body=_clip(memory.summary or memory.content, 140),
        url=f"/recall/{memory.id}",
        memory_id=memory.id,
        created_at=now,
    )


def _send_web_push(*, subscription: PushSubscription, event: NotificationEvent) -> None:
    settings = get_settings()
    subscription_info: dict[str, Any] = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }
    payload = {
        "title": event.title,
        "body": event.body,
        "url": event.url,
        "tag": event.event_key,
        "eventType": event.event_type,
    }
    webpush(
        subscription_info=subscription_info,
        data=json.dumps(payload),
        vapid_private_key=settings.crowscap_vapid_private_key_value,
        vapid_claims={"sub": settings.crowscap_vapid_subject},
    )


def _is_expired_subscription(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code in {404, 410}


def _safe_push_error(exc: Exception) -> str:
    text = str(exc).strip()
    return _clip(text or type(exc).__name__, 240)


def _clip(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."
