from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    ChatMessage,
    Memory,
    NotificationDelivery,
    PushSubscription,
    Reminder,
    Source,
    utc_now,
)
from app.db.session import SessionLocal
from app.schemas.notifications import (
    NotificationEvent,
    PushSubscriptionPayload,
)

logger = get_logger("services.notification")

_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "being",
    "between",
    "could",
    "does",
    "doing",
    "from",
    "have",
    "into",
    "just",
    "more",
    "most",
    "need",
    "should",
    "that",
    "their",
    "there",
    "these",
    "thing",
    "this",
    "those",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}

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


def upsert_native_push_token(
    *,
    db: Session,
    user_id: str,
    token: str,
    platform: str,
    device_name: str | None,
    user_agent: str | None,
) -> PushSubscription:
    existing = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == token))
    if existing is None:
        existing = PushSubscription(
            user_id=user_id,
            endpoint=token,
            p256dh="expo",
            auth="expo",
        )
        db.add(existing)

    existing.user_id = user_id
    existing.p256dh = "expo"
    existing.auth = "expo"
    existing.status = "active"
    existing.user_agent = user_agent
    existing.last_seen_at = utc_now()
    existing.last_error = None
    existing.metadata_json = {
        **(existing.metadata_json or {}),
        "provider": "expo",
        "platform": platform,
        "device_name": device_name,
    }
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

    due_reminder = _select_due_reminder_for_notification(db=db, user_id=user_id, now=now)
    reminder_count = db.scalar(
        select(func.count(Reminder.id)).where(
            Reminder.user_id == user_id,
            Reminder.status == "scheduled",
            Reminder.due_at <= now,
        )
    ) or 0

    due_memory_row = _select_due_memory_for_notification(db=db, user_id=user_id, now=now)
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
            db=db,
            reminder=due_reminder,
            due_count=int(reminder_count) + int(memory_count),
            now=now,
        )
    if due_memory_row is not None:
        due_memory, due_source, surface_reason = due_memory_row
        return _recall_event(
            memory=due_memory,
            source=due_source,
            surface_reason=surface_reason,
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
            if _is_expo_subscription(subscription):
                _send_expo_push(subscription=subscription, event=event)
            else:
                if not settings.push_notifications_configured:
                    last_error = "Web Push is not configured."
                    subscription.last_error = last_error
                    logger.info(
                        "notification.push.skipped reason=vapid_not_configured user_id=%s",
                        user_id,
                    )
                    continue
                if webpush is None:
                    last_error = "Web Push dependency is not installed."
                    subscription.last_error = last_error
                    logger.warning(
                        "notification.push.skipped reason=pywebpush_missing user_id=%s",
                        user_id,
                    )
                    continue
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
            if _is_expired_subscription(exc):
                subscription.status = "disabled"

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


def _select_due_reminder_for_notification(
    *,
    db: Session,
    user_id: str,
    now: datetime,
) -> Reminder | None:
    reminders = db.scalars(
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.status == "scheduled",
            Reminder.due_at <= now,
        )
        .order_by(Reminder.due_at.asc())
        .limit(40)
    ).all()
    for reminder in reminders:
        if not _has_sent_delivery(db=db, event_key=_reminder_event_key(reminder)):
            return reminder
    return None


def generate_notification_copy(
    *,
    context: dict[str, Any],
    default_title: str,
    default_body: str,
) -> tuple[str, str]:
    """Generate grounded notification copy without letting the model invent facts."""
    fallback_title = _clip(default_title, 52)
    fallback_body = _clip(default_body, 168)
    try:
        from app.ai.qwen_client import QwenClient
        qwen = QwenClient()
        system_prompt = (
            "You write push notifications for Crowscap, a private memory app.\n"
            "Use only facts in the provided JSON context. Do not invent source details, dates, deadlines, or claims.\n"
            "Make the notification feel personal, specific, and useful, not like marketing copy.\n"
            "Avoid generic phrases such as 'Discover how', 'Explore', 'Dive into', or 'Unlock'.\n"
            "If a deadline or due phrase is present, make urgency clear by saying tomorrow, today, in 2 days, or the exact phrase provided.\n"
            "Title must be 52 characters or less. Body must be 168 characters or less.\n"
            "Return JSON only: {\"title\": \"...\", \"body\": \"...\"}"
        )
        res = qwen.chat_json(
            system_prompt=system_prompt,
            user_prompt=json.dumps(context, ensure_ascii=True),
        )
        title = str(res.get("title") or fallback_title).strip()
        body = str(res.get("body") or fallback_body).strip()
        return _sanitize_notification_text(title, fallback_title, 52), _sanitize_notification_text(
            body,
            fallback_body,
            168,
        )
    except Exception:
        return fallback_title, fallback_body


def _reminder_event(
    *,
    db: Session,
    reminder: Reminder,
    due_count: int,
    now: datetime,
) -> NotificationEvent:
    due_phrase = _due_phrase(reminder.due_at, now)
    linked_memory, linked_source = _linked_memory_context(db=db, reminder=reminder)
    title_fallback = _deadline_title(reminder=reminder, due_phrase=due_phrase)
    body_fallback = _reminder_body_fallback(
        reminder=reminder,
        due_phrase=due_phrase,
        memory=linked_memory,
        source=linked_source,
    )
    title, body = generate_notification_copy(
        context={
            "notification_type": "reminder",
            "due_phrase": due_phrase,
            "reminder_text": reminder.content,
            "saved_at_phrase": _saved_phrase(reminder.created_at, now),
            "linked_memory": _memory_context(memory=linked_memory, source=linked_source) if linked_memory else None,
            "goal": "Get the user to act at the right time without sounding generic.",
        },
        default_title=title_fallback,
        default_body=body_fallback,
    )
    return NotificationEvent(
        event_id=str(uuid.uuid4()),
        event_key=_reminder_event_key(reminder),
        event_type="reminder_due",
        due_count=due_count,
        title=title,
        body=body,
        notification_title=title,
        notification_body=body,
        url="/recall",
        reminder_id=reminder.id,
        created_at=now,
    )


def _recall_event(
    *,
    memory: Memory,
    source: Source,
    surface_reason: str,
    due_count: int,
    now: datetime,
) -> NotificationEvent:
    saved_phrase = _saved_phrase(memory.created_at, now)
    content = memory.summary or memory.content
    title, body = generate_notification_copy(
        context={
            "notification_type": "recall",
            "saved_at_phrase": saved_phrase,
            "source_type": source.source_type,
            "source_title": source.title,
            "memory_type": memory.memory_type,
            "user_intent": _capture_intent(memory),
            "memory_content": content,
            "surface_reason": surface_reason,
            "goal": "Make the saved memory feel worth reopening now.",
        },
        default_title=_recall_title_fallback(memory=memory, source=source),
        default_body=_recall_body_fallback(
            memory=memory,
            source=source,
            saved_phrase=saved_phrase,
            surface_reason=surface_reason,
        ),
    )
    return NotificationEvent(
        event_id=str(uuid.uuid4()),
        event_key=_recall_event_key(memory),
        event_type="recall_due",
        due_count=due_count,
        title=title,
        body=body,
        notification_title=title,
        notification_body=body,
        url=f"/recall/{memory.id}",
        memory_id=memory.id,
        created_at=now,
    )


def _select_due_memory_for_notification(
    *,
    db: Session,
    user_id: str,
    now: datetime,
) -> tuple[Memory, Source, str] | None:
    if _recall_push_is_throttled(db=db, user_id=user_id, now=now):
        return None

    rows = list(
        db.execute(
            select(Memory, Source)
            .join(Source, Memory.source_id == Source.id)
            .where(
                Memory.user_id == user_id,
                Memory.status == "active",
                Memory.next_review_at.is_not(None),
                Memory.next_review_at <= now,
            )
            .order_by(Memory.next_review_at.asc())
            .limit(80)
        ).all()
    )
    if not rows:
        return None

    rows = [
        (memory, source)
        for memory, source in rows
        if not _has_sent_delivery(db=db, event_key=_recall_event_key(memory))
    ]
    if not rows:
        return None

    recent_context = _recent_activity_terms(db=db, user_id=user_id)
    scored = [
        _score_notification_memory(
            memory=memory,
            source=source,
            now=now,
            recent_context=recent_context,
        )
        for memory, source in rows
    ]
    scored.sort(key=lambda item: (-item[0], _aware(item[1].next_review_at).timestamp()))
    _score, memory, source, reason = scored[0]
    return memory, source, reason


def _recall_push_is_throttled(*, db: Session, user_id: str, now: datetime) -> bool:
    settings = get_settings()
    cooldown_minutes = max(0, settings.crowscap_recall_push_cooldown_minutes)
    daily_limit = max(1, settings.crowscap_recall_push_daily_limit)

    if cooldown_minutes:
        cooldown_start = now - timedelta(minutes=cooldown_minutes)
        recent_delivery = db.scalar(
            select(NotificationDelivery.id)
            .where(
                NotificationDelivery.user_id == user_id,
                NotificationDelivery.event_type == "recall_due",
                NotificationDelivery.status == "sent",
                NotificationDelivery.sent_at.is_not(None),
                NotificationDelivery.sent_at >= cooldown_start,
            )
            .limit(1)
        )
        if recent_delivery is not None:
            return True

    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = db.scalar(
        select(func.count(NotificationDelivery.id)).where(
            NotificationDelivery.user_id == user_id,
            NotificationDelivery.event_type == "recall_due",
            NotificationDelivery.status == "sent",
            NotificationDelivery.sent_at.is_not(None),
            NotificationDelivery.sent_at >= day_start,
        )
    ) or 0
    return int(sent_today) >= daily_limit


def _score_notification_memory(
    *,
    memory: Memory,
    source: Source,
    now: datetime,
    recent_context: set[str],
) -> tuple[float, Memory, Source, str]:
    overdue_days = max(0.0, (now - _aware(memory.next_review_at)).total_seconds() / 86_400) if memory.next_review_at else 0.0
    confidence_score = _confidence_score(memory.confidence)
    source_score = _source_score(memory.source_strength, source.source_type)
    intent_score = _intent_score(_capture_intent(memory))
    type_score = _memory_type_score(memory.memory_type)
    recall_need = max(0.0, min(1.0, 1.0 - float(memory.recall_score or 0.0)))
    context_score = _token_overlap_score(
        " ".join(
            part
            for part in (
                source.title or "",
                memory.summary or "",
                memory.content,
                memory.memory_type,
                _capture_intent(memory) or "",
            )
            if part
        ),
        recent_context,
    )
    age_score = min(overdue_days, 21.0) / 21.0

    score = (
        context_score * 0.30
        + confidence_score * 0.18
        + source_score * 0.16
        + intent_score * 0.14
        + recall_need * 0.12
        + age_score * 0.07
        + type_score * 0.03
    )

    if context_score >= 0.18:
        reason = "It connects with what you have been working on recently."
    elif intent_score >= 0.75:
        reason = "You saved it with a clear reason, so it is worth bringing back."
    elif recall_need >= 0.45:
        reason = "Your recall score says this needs a refresh."
    elif source_score >= 0.75:
        reason = "It came from a stronger source and is due for review."
    else:
        reason = "It is due for a quick revisit."

    return score, memory, source, reason


def _linked_memory_context(
    *,
    db: Session,
    reminder: Reminder,
) -> tuple[Memory | None, Source | None]:
    if not reminder.memory_id:
        return None, None
    row = db.execute(
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.id == reminder.memory_id, Memory.user_id == reminder.user_id)
        .limit(1)
    ).first()
    if row is None:
        return None, None
    memory, source = row
    return memory, source


def _memory_context(*, memory: Memory, source: Source | None) -> dict[str, Any]:
    return {
        "source_type": source.source_type if source else None,
        "source_title": source.title if source else None,
        "memory_type": memory.memory_type,
        "content": memory.summary or memory.content,
        "intent": _capture_intent(memory),
    }


def _capture_intent(memory: Memory) -> str | None:
    capture = getattr(memory, "capture", None)
    if capture is None:
        return None
    return capture.user_intent_text or capture.user_note


def _deadline_title(*, reminder: Reminder, due_phrase: str) -> str:
    lowered = reminder.content.lower()
    if any(term in lowered for term in ("deadline", "apply", "application", "grant", "hackathon", "submit")):
        return f"Deadline {due_phrase}"
    if due_phrase in {"today", "tomorrow"} or due_phrase.startswith("in "):
        return f"Reminder {due_phrase}"
    return "Reminder ready"


def _reminder_body_fallback(
    *,
    reminder: Reminder,
    due_phrase: str,
    memory: Memory | None,
    source: Source | None,
) -> str:
    if memory is not None:
        source_label = _source_label(source)
        snippet = _clip(memory.summary or memory.content, 92)
        return _clip(f"You saved this {source_label} for {due_phrase}. {snippet}", 168)
    return _clip(f"{due_phrase.capitalize()}: {reminder.content}", 168)


def _recall_title_fallback(*, memory: Memory, source: Source) -> str:
    if source.source_type in {"youtube", "video"}:
        return "Your saved video is ready"
    if source.source_type in {"article", "url"}:
        return "Your saved article is ready"
    if memory.memory_type == "action":
        return "Action worth revisiting"
    if memory.memory_type == "warning":
        return "A risk worth checking"
    return "A thought is ready"


def _recall_body_fallback(
    *,
    memory: Memory,
    source: Source,
    saved_phrase: str,
    surface_reason: str,
) -> str:
    source_label = _source_label(source)
    intent = _capture_intent(memory)
    content = _clip(memory.summary or memory.content, 105)
    if intent:
        return _clip(f"You saved this {source_label} {saved_phrase} for {intent}. {content}", 168)
    return _clip(f"You saved this {source_label} {saved_phrase}. {content}", 168)


def _source_label(source: Source | None) -> str:
    if source is None:
        return "memory"
    if source.source_type == "youtube":
        return "video"
    if source.source_type in {"url", "article"}:
        return "article"
    if source.source_type == "pdf":
        return "PDF"
    if source.source_type == "reference":
        return "link"
    return source.source_type.replace("_", " ")


def _due_phrase(due_at: datetime, now: datetime) -> str:
    due = _aware(due_at)
    current = _aware(now)
    day_delta = (due.date() - current.date()).days
    if day_delta < 0:
        if day_delta == -1:
            return "yesterday"
        return f"{abs(day_delta)} days ago"
    if day_delta == 0:
        return "today"
    if day_delta == 1:
        return "tomorrow"
    if day_delta <= 7:
        return f"in {day_delta} days"
    return f"on {due.strftime('%b %d')}"


def _saved_phrase(saved_at: datetime | None, now: datetime) -> str:
    if saved_at is None:
        return "recently"
    saved = _aware(saved_at)
    current = _aware(now)
    day_delta = (current.date() - saved.date()).days
    if day_delta <= 0:
        return "today"
    if day_delta == 1:
        return "yesterday"
    if day_delta < 14:
        return f"{day_delta} days ago"
    if day_delta < 60:
        weeks = max(2, round(day_delta / 7))
        return f"{weeks} weeks ago"
    months = max(2, round(day_delta / 30))
    return f"{months} months ago"


def _recent_activity_terms(*, db: Session, user_id: str) -> set[str]:
    pieces = list(
        db.scalars(
            select(ChatMessage.content)
            .where(ChatMessage.user_id == user_id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.desc())
            .limit(8)
        ).all()
    )
    memory_rows = db.execute(
        select(Memory.content, Memory.summary, Source.title)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.user_id == user_id, Memory.status == "active")
        .order_by(Memory.created_at.desc())
        .limit(8)
    ).all()
    for content, summary, title in memory_rows:
        pieces.extend(piece for piece in (content, summary, title) if piece)
    return _tokens(" ".join(piece for piece in pieces if piece))


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]{3,}", text.lower())
        if token not in _STOPWORDS
    }


def _token_overlap_score(text: str, recent_context: set[str]) -> float:
    if not recent_context:
        return 0.0
    memory_tokens = _tokens(text)
    if not memory_tokens:
        return 0.0
    return min(1.0, len(memory_tokens & recent_context) / max(4.0, len(memory_tokens) ** 0.5))


def _confidence_score(value: str | None) -> float:
    return {
        "high": 1.0,
        "medium": 0.68,
        "low": 0.35,
        "unknown": 0.28,
    }.get((value or "unknown").lower(), 0.28)


def _source_score(source_strength: str | None, source_type: str | None) -> float:
    base = {
        "strong": 1.0,
        "moderate": 0.66,
        "weak": 0.34,
        "unknown": 0.38,
    }.get((source_strength or "unknown").lower(), 0.38)
    if source_type in {"youtube", "article", "pdf"}:
        base += 0.08
    return min(1.0, base)


def _intent_score(intent: str | None) -> float:
    if not intent:
        return 0.25
    lowered = intent.lower()
    if any(term in lowered for term in ("apply", "yc", "deadline", "grant", "hackathon", "launch", "customer", "build")):
        return 1.0
    return 0.75


def _memory_type_score(memory_type: str | None) -> float:
    return {
        "action": 1.0,
        "warning": 0.9,
        "principle": 0.82,
        "claim": 0.74,
        "question": 0.7,
        "reference": 0.56,
        "intention": 0.86,
    }.get((memory_type or "").lower(), 0.5)


def _sanitize_notification_text(value: str, fallback: str, limit: int) -> str:
    compact = " ".join(value.split()).strip()
    if not compact:
        return fallback
    lowered = compact.lower()
    banned_openers = ("discover how", "explore", "dive into", "unlock")
    if lowered.startswith(banned_openers):
        return fallback
    return _clip(compact, limit)


def _reminder_event_key(reminder: Reminder) -> str:
    return f"reminder_due:{reminder.id}:{reminder.due_at.isoformat()}"


def _recall_event_key(memory: Memory) -> str:
    due_key = memory.next_review_at.isoformat() if memory.next_review_at else "due"
    return f"recall_due:{memory.id}:{due_key}"


def _has_sent_delivery(*, db: Session, event_key: str) -> bool:
    delivery = db.scalar(
        select(NotificationDelivery.id).where(
            NotificationDelivery.event_key == event_key,
            NotificationDelivery.channel == "web_push",
            NotificationDelivery.status == "sent",
        )
    )
    return delivery is not None


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value



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


def _send_expo_push(*, subscription: PushSubscription, event: NotificationEvent) -> None:
    settings = get_settings()
    payload = {
        "to": subscription.endpoint,
        "title": event.title,
        "body": event.body,
        "sound": "default",
        "priority": "high",
        "channelId": "default",
        "data": {
            "url": event.url,
            "tag": event.event_key,
            "eventType": event.event_type,
            "reminderId": event.reminder_id,
            "memoryId": event.memory_id,
        },
    }
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
    }
    if settings.expo_push_access_token_value:
        headers["Authorization"] = f"Bearer {settings.expo_push_access_token_value}"

    response = httpx.post(
        "https://exp.host/--/api/v2/push/send",
        json=payload,
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
    tickets = data.get("data")
    ticket = tickets[0] if isinstance(tickets, list) and tickets else tickets
    if isinstance(ticket, dict) and ticket.get("status") == "error":
        details = ticket.get("details") or {}
        error_code = details.get("error") or ticket.get("message") or "expo_push_error"
        raise RuntimeError(str(error_code))


def _is_expo_subscription(subscription: PushSubscription) -> bool:
    provider = (subscription.metadata_json or {}).get("provider")
    return provider == "expo" or subscription.endpoint.startswith(
        ("ExponentPushToken[", "ExpoPushToken[")
    )


def _is_expired_subscription(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code in {404, 410}:
        return True
    return "devicenotregistered" in str(exc).replace("_", "").lower()


def _safe_push_error(exc: Exception) -> str:
    text = str(exc).strip()
    return _clip(text or type(exc).__name__, 240)


def _clip(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."
