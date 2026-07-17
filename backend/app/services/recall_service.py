from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Memory, MemoryRelation, Reminder, Source, UserPreference, utc_now
from app.schemas.recall import (
    DueRecallMemoryResponse,
    DueRecallsResponse,
    DueReminderResponse,
    RecallRelationshipResponse,
)
from app.services.preference_service import get_or_create_user_preferences

logger = get_logger("services.recall")


def get_due_recalls(
    *,
    db: Session,
    limit: int,
    user_id: str | None = None,
) -> DueRecallsResponse:
    now = utc_now()
    logger.info("\U0001f514 recall.due.start limit=%s", limit)

    rows = _load_due_memories(db=db, now=now, limit=limit, user_id=user_id)
    memories = [memory for memory, _source in rows]
    relationships = _relationships_for_recall_memories(db=db, memories=memories, user_id=user_id)
    preferences = get_or_create_user_preferences(db=db, user_id=user_id)

    response_memories = [
        DueRecallMemoryResponse(
            memory_id=memory.id,
            source_id=source.id,
            source_title=source.title,
            memory_type=memory.memory_type,
            epistemic_label=memory.epistemic_label,
            content=memory.content,
            summary=memory.summary,
            confidence=memory.confidence,
            confidence_reason=memory.confidence_reason,
            source_strength=memory.source_strength,
            next_review_at=_aware(memory.next_review_at),
            last_reviewed_at=_aware(memory.last_reviewed_at) if memory.last_reviewed_at else None,
            review_count=memory.review_count,
            recall_score=memory.recall_score,
            overdue_seconds=_overdue_seconds(now=now, next_review_at=memory.next_review_at),
            recall_prompt=_recall_prompt(
                memory=memory,
                relationships=relationships.get(memory.id, []),
                preferences=preferences,
            ),
            epistemic_caution=_epistemic_caution(memory=memory),
            relationships=relationships.get(memory.id, []),
        )
        for memory, source in rows
    ]

    due_reminders = _load_due_reminders(db=db, now=now, limit=limit, user_id=user_id)
    response_reminders = [
        DueReminderResponse(
            reminder_id=reminder.id,
            content=reminder.content,
            due_at=_aware(reminder.due_at),
            overdue_seconds=_overdue_seconds(now=now, next_review_at=reminder.due_at),
            save_as_memory=bool(reminder.save_as_memory),
            memory_id=reminder.memory_id,
            status=reminder.status,
        )
        for reminder in due_reminders
    ]

    logger.info(
        "\u2705 recall.due.complete memories=%s reminders=%s",
        len(response_memories),
        len(response_reminders),
    )
    return DueRecallsResponse(
        due_count=len(response_memories) + len(response_reminders),
        now=now,
        memories=response_memories,
        reminders=response_reminders,
    )


def _load_due_memories(
    *,
    db: Session,
    now: datetime,
    limit: int,
    user_id: str | None,
) -> list[tuple[Memory, Source]]:
    query = (
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.status == "active")
        .where(Memory.next_review_at.is_not(None))
        .where(Memory.next_review_at <= now)
        .order_by(Memory.next_review_at.asc())
        .limit(limit)
    )
    if user_id is None:
        query = query.where(Memory.user_id.is_(None))
    else:
        query = query.where(Memory.user_id == user_id)

    return list(db.execute(query).all())


def _load_due_reminders(
    *,
    db: Session,
    now: datetime,
    limit: int,
    user_id: str | None,
) -> list[Reminder]:
    query = (
        select(Reminder)
        .where(Reminder.status == "scheduled")
        .where(Reminder.memory_id.is_(None))
        .where(Reminder.due_at <= now)
        .order_by(Reminder.due_at.asc())
        .limit(limit)
    )
    if user_id is None:
        query = query.where(Reminder.user_id.is_(None))
    else:
        query = query.where(Reminder.user_id == user_id)
    return list(db.scalars(query).all())


def _relationships_for_recall_memories(
    *,
    db: Session,
    memories: list[Memory],
    user_id: str | None = None,
) -> dict[str, list[RecallRelationshipResponse]]:
    memory_ids = [memory.id for memory in memories]
    if not memory_ids:
        return {}

    relation_query = select(MemoryRelation).where(
        or_(
            MemoryRelation.source_memory_id.in_(memory_ids),
            MemoryRelation.target_memory_id.in_(memory_ids),
        )
    )
    if user_id is None:
        relation_query = relation_query.where(MemoryRelation.user_id.is_(None))
    else:
        relation_query = relation_query.where(MemoryRelation.user_id == user_id)
    relation_rows = list(db.scalars(relation_query).all())
    related_ids = {
        relation.target_memory_id
        for relation in relation_rows
        if relation.source_memory_id in memory_ids
    } | {
        relation.source_memory_id
        for relation in relation_rows
        if relation.target_memory_id in memory_ids
    }
    related_memories = {
        memory.id: memory
        for memory in db.scalars(select(Memory).where(Memory.id.in_(related_ids))).all()
    }

    relationships: dict[str, list[RecallRelationshipResponse]] = {memory_id: [] for memory_id in memory_ids}
    for relation in relation_rows:
        if relation.source_memory_id in relationships:
            related_memory = related_memories.get(relation.target_memory_id)
            if related_memory is None:
                continue
            relationships[relation.source_memory_id].append(
                RecallRelationshipResponse(
                    related_memory_id=related_memory.id,
                    related_memory_content=related_memory.content,
                    relationship_type=relation.relation_type,
                    strength=relation.strength,
                    explanation=relation.explanation,
                    direction="outgoing",
                )
            )

        if relation.target_memory_id in relationships:
            related_memory = related_memories.get(relation.source_memory_id)
            if related_memory is None:
                continue
            relationships[relation.target_memory_id].append(
                RecallRelationshipResponse(
                    related_memory_id=related_memory.id,
                    related_memory_content=related_memory.content,
                    relationship_type=relation.relation_type,
                    strength=relation.strength,
                    explanation=relation.explanation,
                    direction="incoming",
                )
            )

    return relationships


def _overdue_seconds(*, now: datetime, next_review_at: datetime | None) -> int:
    if next_review_at is None:
        return 0
    return max(0, int((now - _aware(next_review_at)).total_seconds()))


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _recall_prompt(
    *,
    memory: Memory,
    relationships: list[RecallRelationshipResponse],
    preferences: UserPreference | None = None,
) -> str:
    answer_style = preferences.answer_style if preferences else None
    evidence_strictness = preferences.evidence_strictness if preferences else "balanced"
    challenge_style = preferences.challenge_style if preferences else "balanced"

    if any(relationship.relationship_type in {"conflicts", "tension"} for relationship in relationships):
        if challenge_style == "direct":
            return "Where does this idea hold, and where could the competing view be right?"
        return "Connect this idea with the related view. Where might each one apply?"
    if memory.memory_type == "action":
        if answer_style == "concise":
            return "What is one real situation where this action would matter?"
        return "Explain why this action matters and how you would apply it in a real situation."
    if memory.memory_type in {"claim", "principle"} and memory.source_strength in {"weak", "moderate"}:
        if evidence_strictness == "strict":
            return "Restate this idea, then name what evidence would make you trust it more."
        return "Explain this idea in your own words, then name what evidence or context it still needs."
    if memory.memory_type == "warning":
        return "What mistake is this warning trying to prevent, and when does it matter?"
    if answer_style == "concise":
        return "What does this mean in your own words?"
    return "Explain this idea in your own words and why it matters."


def _epistemic_caution(*, memory: Memory) -> str | None:
    if memory.epistemic_label in {"opinion", "advice", "anecdote", "prediction"}:
        return (
            f"This was saved as {memory.epistemic_label.replace('_', ' ')}, "
            "not as a verified fact."
        )
    if memory.source_strength in {"weak", "moderate"}:
        return (
            f"The source strength is {memory.source_strength}; recall the idea, "
            "but keep its evidence limits in view."
        )
    return None
