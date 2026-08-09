from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import ChatMessage, Memory, MemoryRelation, Reminder, Source, UserPreference, utc_now
from app.schemas.recall import (
    DueRecallMemoryResponse,
    DueRecallsResponse,
    DueReminderResponse,
    RecallRelationshipResponse,
)
from app.services.preference_service import get_or_create_user_preferences

logger = get_logger("services.recall")

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


def get_due_recalls(
    *,
    db: Session,
    limit: int,
    user_id: str | None = None,
    target_memory_id: str | None = None,
) -> DueRecallsResponse:
    now = utc_now()
    logger.info("🔔 recall.due.start limit=%s target=%s", limit, target_memory_id)

    rows = _load_due_memories(
        db=db,
        now=now,
        limit=limit,
        user_id=user_id,
        target_memory_id=target_memory_id,
    )
    memories = [memory for memory, _source, _reason, _pinned in rows]
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
            summary=_build_recall_summary(memory=memory, source=source),
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
            human_title=_human_recall_title(memory=memory, source=source, now=now),
            human_prompt=_human_recall_prompt(memory=memory, source=source),
            pinned_from_notification=pinned,
            epistemic_caution=_epistemic_caution(memory=memory),
            surface_reason=surface_reason,
            relationships=relationships.get(memory.id, []),
        )
        for memory, source, surface_reason, pinned in rows
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
    target_memory_id: str | None = None,
) -> list[tuple[Memory, Source, str, bool]]:
    pool_limit = max(limit * 6, 60)
    query = (
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.status == "active")
        .where(Memory.next_review_at.is_not(None))
        .where(Memory.next_review_at <= now)
        .order_by(Memory.next_review_at.asc())
        .limit(pool_limit)
    )
    if user_id is None:
        query = query.where(Memory.user_id.is_(None))
    else:
        query = query.where(Memory.user_id == user_id)

    rows = list(db.execute(query).all())
    recent_context = _recent_activity_context(db=db, user_id=user_id)
    scored_rows = [
        _score_due_memory(
            now=now,
            memory=memory,
            source=source,
            recent_context=recent_context,
        )
        for memory, source in rows
    ]
    scored_rows.sort(
        key=lambda row: (
            -row[0],
            _aware(row[1].next_review_at).timestamp() if row[1].next_review_at else 0,
        ),
    )

    selected = [(memory, source, reason, False) for _score, memory, source, reason in scored_rows[:limit]]

    if target_memory_id:
        target_query = (
            select(Memory, Source)
            .join(Source, Memory.source_id == Source.id)
            .where(Memory.id == target_memory_id)
            .where(Memory.status == "active")
        )
        if user_id is not None:
            target_query = target_query.where(Memory.user_id == user_id)
        target_row = db.execute(target_query).first()
        if target_row:
            t_mem, t_src = target_row
            selected = [
                (m, s, r, p) for m, s, r, p in selected if m.id != t_mem.id
            ]
            selected.insert(0, (t_mem, t_src, "From Today's Nudge", True))

    logger.info(
        "🧭 recall.selection ranked_pool=%s selected=%s recent_terms=%s target_pinned=%s",
        len(rows),
        len(selected),
        len(recent_context),
        bool(target_memory_id),
    )
    return selected


def _clean_title(raw_title: str) -> str:
    cleaned = urllib.parse.unquote(raw_title).strip()
    if cleaned.isupper() and len(cleaned) > 4:
        name, dot, ext = cleaned.rpartition(".")
        if dot:
            cleaned = name.title() + dot + ext.lower()
        else:
            cleaned = cleaned.title()
    return cleaned


def _build_recall_summary(*, memory: Memory, source: Source) -> str:
    clean_title = _clean_title(source.title) if (source.title and source.title != "Captured text") else None

    # If memory already has a detailed summary (> 60 chars), use it
    if memory.summary and len(memory.summary.strip()) >= 60:
        sum_text = memory.summary.strip()
        if clean_title and not sum_text.startswith("#"):
            return f"### {clean_title}\n\n{sum_text}"
        return sum_text

    # If source has raw_text (e.g., PDF text, article text), format a structured summary
    raw_text = getattr(source, "raw_text", None)
    if raw_text and len(raw_text.strip()) > 30:
        orig = raw_text.strip()
        lines = [l.strip() for l in orig.split("\n") if l.strip() and not l.strip().startswith("http")]
        bullet_points = lines[:6]
        formatted_bullets = "\n".join(f"- {b}" if not b.startswith("-") and not b.startswith("#") else b for b in bullet_points)
        if clean_title:
            return f"### {clean_title}\n\n{formatted_bullets}"
        return formatted_bullets

    # Fallback combining memory summary/content and source title
    main_text = memory.summary or memory.content or "Saved memory item."
    if clean_title:
        return f"### {clean_title}\n\n- {main_text}"
    return main_text


def _human_recall_title(*, memory: Memory, source: Source, now: datetime) -> str:
    created_at = _aware(memory.created_at or now)
    days_ago = max(0, (now - created_at).days)
    time_str = (
        "Today"
        if days_ago == 0
        else ("Yesterday" if days_ago == 1 else f"{days_ago} days ago")
    )
    if source.title and source.title != "Captured text":
        clean_name = _clean_title(source.title)
        title_snippet = clean_name[:32] + "..." if len(clean_name) > 32 else clean_name
        return f"{time_str} · {title_snippet}"
    source_kind = (
        "YouTube"
        if source.source_type == "youtube"
        else (
            "PDF"
            if source.source_type == "pdf"
            else ("Article" if source.source_type == "article" else "Saved note")
        )
    )
    return f"{time_str} · {source_kind}"


def _human_recall_prompt(*, memory: Memory, source: Source) -> str:
    source_title = _clean_title(source.title) if (source.title and source.title != "Captured text") else None
    content_text = memory.summary or memory.content
    snippet = content_text[:90].strip() + "..." if len(content_text) > 90 else content_text.strip()

    if source_title:
        if source.source_type in {"pdf", "file", "url", "youtube", "article"}:
            return f"You saved '{source_title}'. Would you like to review it?"
        if memory.memory_type == "intention":
            return f"You saved an intention from '{source_title}'. Still something you want to do?"
        if memory.memory_type == "action":
            return f"You saved an action item from '{source_title}'. Would you like to review it?"
        if memory.memory_type == "question":
            return f"You saved a question from '{source_title}'. Still unresolved?"
        return f"You saved '{source_title}'. Would you like to review it?"

    if memory.memory_type == "intention":
        return f"You saved an intention: '{snippet}'. Still something you want to do?"
    if memory.memory_type == "action":
        return f"You saved an action item: '{snippet}'. Have you tried this out?"
    if memory.memory_type == "question":
        return f"You saved a question: '{snippet}'. Still unresolved?"
    return f"You saved: '{snippet}'. Do you still want to revisit this?"


def _recent_activity_context(*, db: Session, user_id: str | None) -> set[str]:
    """Small, explainable context window for recall ranking.

    We intentionally avoid an LLM call here. Recall should stay fast and the
    scoring should be understandable: recent user words and recent saved ideas
    nudge due memories up when they overlap.
    """

    message_query = (
        select(ChatMessage.content)
        .where(ChatMessage.role == "user")
        .order_by(ChatMessage.created_at.desc())
        .limit(8)
    )
    memory_query = (
        select(Memory.content, Memory.summary, Source.title)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.status == "active")
        .order_by(Memory.created_at.desc())
        .limit(8)
    )
    if user_id is None:
        message_query = message_query.where(ChatMessage.user_id.is_(None))
        memory_query = memory_query.where(Memory.user_id.is_(None))
    else:
        message_query = message_query.where(ChatMessage.user_id == user_id)
        memory_query = memory_query.where(Memory.user_id == user_id)

    pieces: list[str] = [content for content in db.scalars(message_query).all() if content]
    for content, summary, title in db.execute(memory_query).all():
        pieces.extend(piece for piece in (content, summary, title) if piece)

    return _tokens(" ".join(pieces))


def _score_due_memory(
    *,
    now: datetime,
    memory: Memory,
    source: Source,
    recent_context: set[str],
) -> tuple[float, Memory, Source, str]:
    overdue_days = _overdue_seconds(now=now, next_review_at=memory.next_review_at) / 86_400
    context_score = _token_overlap_score(
        " ".join(
            part
            for part in (
                memory.content,
                memory.summary or "",
                source.title or "",
                memory.memory_type,
            )
            if part
        ),
        recent_context,
    )
    recall_need = max(0.0, min(1.0, 1.0 - float(memory.recall_score or 0.0)))
    fragility_bonus = 0.0
    if memory.confidence in {"low", "unknown"}:
        fragility_bonus += 0.05
    if memory.source_strength in {"weak", "moderate", "unknown"}:
        fragility_bonus += 0.04
    if memory.epistemic_label in {"opinion", "advice", "prediction", "anecdote"}:
        fragility_bonus += 0.03

    score = (
        min(overdue_days, 30.0) / 30.0 * 0.38
        + context_score * 0.36
        + recall_need * 0.18
        + fragility_bonus
    )
    return score, memory, source, _surface_reason(
        memory=memory,
        source=source,
        context_score=context_score,
        overdue_days=overdue_days,
        recall_need=recall_need,
    )


def _surface_reason(
    *,
    memory: Memory,
    source: Source,
    context_score: float,
    overdue_days: float,
    recall_need: float,
) -> str:
    if context_score >= 0.18:
        return "Surfaced because it connects with what you have been discussing or saving recently."
    if recall_need >= 0.45:
        return "Surfaced because this idea is due and your recall score says it needs a light refresh."
    if overdue_days >= 7:
        title = source.title or "this source"
        return f"Surfaced because you saved it from {title} a while ago and it is ready to revisit."
    if memory.memory_type == "action":
        return "Surfaced because this saved action is ready to reconnect with real work."
    return "Surfaced because it is ready for a quick check-in."


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
    overlap = memory_tokens & recent_context
    return min(1.0, len(overlap) / max(4.0, len(memory_tokens) ** 0.5))


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
            return "Have you applied this? What happened, or what is stopping you?"
        return "Have you applied this in anything you are building? What happened, or what would be the next small test?"
    if memory.memory_type == "warning":
        return "Have you seen this risk play out? What would you watch for next time?"
    if memory.memory_type == "definition":
        return "Can you explain this in your own words without looking at the source?"
    if memory.memory_type == "example":
        return "What larger idea does this example prove, limit, or complicate?"
    if memory.memory_type == "question":
        return "Does this still feel unresolved? What answer or evidence would move it forward?"
    if memory.memory_type in {"reference", "quote"}:
        return "Why did this feel worth keeping, and when would you reach for it again?"
    if memory.memory_type == "intention":
        return "Do you still want to follow up on this, or should Crowscap stop surfacing it?"
    if memory.memory_type in {"claim", "principle"} and memory.source_strength in {"weak", "moderate"}:
        if evidence_strictness == "strict":
            return "Restate this idea, then name what evidence would make you trust it more."
        return "Explain this idea in your own words, then name what evidence or context it still needs."
    if memory.memory_type == "principle":
        return "Where does this principle apply in your current work, and where might it fail?"
    if memory.memory_type == "claim":
        return "What would make this claim stronger, weaker, or more specific?"
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
