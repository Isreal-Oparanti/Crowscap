from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Reminder, utc_now
from app.schemas.reminder import ReminderResponse

logger = get_logger("services.reminder")


def create_reminder(
    *,
    db: Session,
    content: str,
    due_at: datetime,
    conversation_id: str | None = None,
    memory_id: str | None = None,
    save_as_memory: bool = False,
    user_id: str | None = None,
    metadata_json: dict | None = None,
) -> ReminderResponse:
    reminder = Reminder(
        user_id=user_id,
        conversation_id=conversation_id,
        memory_id=memory_id,
        content=content.strip(),
        due_at=due_at,
        status="scheduled",
        save_as_memory=1 if save_as_memory else 0,
        metadata_json=metadata_json or {},
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder_response(reminder)


def reminder_response(reminder: Reminder) -> ReminderResponse:
    return ReminderResponse(
        id=reminder.id,
        content=reminder.content,
        due_at=reminder.due_at,
        status=reminder.status,
        save_as_memory=bool(reminder.save_as_memory),
        memory_id=reminder.memory_id,
        conversation_id=reminder.conversation_id,
        created_at=reminder.created_at,
    )


def complete_reminder(
    *,
    db: Session,
    reminder_id: str,
    user_id: str | None = None,
) -> ReminderResponse:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        raise LookupError("Reminder was not found.")
    if user_id is None and reminder.user_id is not None:
        raise LookupError("Reminder was not found.")
    if user_id is not None and reminder.user_id != user_id:
        raise LookupError("Reminder was not found.")

    reminder.status = "completed"
    reminder.delivered_at = reminder.delivered_at or utc_now()
    db.commit()
    db.refresh(reminder)
    logger.info("\u2705 reminder.completed reminder_id=%s", reminder.id)
    return reminder_response(reminder)


def snooze_reminder(
    *,
    db: Session,
    reminder_id: str,
    minutes: int,
    user_id: str | None = None,
) -> ReminderResponse:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        raise LookupError("Reminder was not found.")
    if user_id is None and reminder.user_id is not None:
        raise LookupError("Reminder was not found.")
    if user_id is not None and reminder.user_id != user_id:
        raise LookupError("Reminder was not found.")
    if reminder.status != "scheduled":
        raise ValueError("Only scheduled reminders can be snoozed.")

    now = utc_now()
    reminder.due_at = now + timedelta(minutes=minutes)
    reminder.delivered_at = now
    metadata = dict(reminder.metadata_json or {})
    metadata["last_snoozed_at"] = now.isoformat()
    metadata["last_snoozed_minutes"] = minutes
    reminder.metadata_json = metadata
    db.commit()
    db.refresh(reminder)
    logger.info(
        "\U0001f634 reminder.snoozed reminder_id=%s minutes=%s due_at=%s",
        reminder.id,
        minutes,
        reminder.due_at.isoformat(),
    )
    return reminder_response(reminder)
