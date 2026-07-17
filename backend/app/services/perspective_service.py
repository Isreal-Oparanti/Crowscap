from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Memory, MemoryPerspectiveNote, utc_now
from app.schemas.perspective import (
    PerspectiveNoteDecisionResponse,
    PerspectiveNoteListResponse,
    PerspectiveNoteResponse,
)

logger = get_logger("services.perspective")

ELIGIBLE_MEMORY_TYPES = {"claim", "principle", "framework", "prediction", "warning"}
ONE_SIDED_LABELS = {"opinion", "advice", "prediction", "framework", "unresolved"}
ACTIVE_NOTE_STATUSES = {"queued", "surfaced"}


def queue_perspective_notes_for_memories(
    *,
    db: Session,
    memories: list[Memory],
    user_id: str | None,
    surface_after_days: int = 3,
) -> list[MemoryPerspectiveNote]:
    notes: list[MemoryPerspectiveNote] = []
    for memory in memories:
        if not _should_queue_perspective(memory):
            continue
        if _has_active_note(db=db, memory_id=memory.id):
            continue

        note = MemoryPerspectiveNote(
            user_id=user_id,
            memory_id=memory.id,
            status="queued",
            perspective_type=_perspective_type(memory),
            title=_title_for(memory),
            content=_content_for(memory),
            suggested_query=_suggested_query_for(memory),
            confidence="medium",
            surface_after_at=utc_now() + timedelta(days=surface_after_days),
            metadata_json={
                "reason": "under_evidenced_or_one_sided_memory",
                "memory_type": memory.memory_type,
                "epistemic_label": memory.epistemic_label,
                "source_strength": memory.source_strength,
                "memory_confidence": memory.confidence,
            },
        )
        db.add(note)
        notes.append(note)

    if notes:
        db.flush()
        logger.info("\U0001f9ed perspective.queued notes=%s", len(notes))
    return notes


def list_due_perspective_notes(
    *,
    db: Session,
    user_id: str | None,
    limit: int = 10,
    include_future: bool = False,
) -> PerspectiveNoteListResponse:
    query = (
        select(MemoryPerspectiveNote)
        .where(MemoryPerspectiveNote.user_id.is_(None) if user_id is None else MemoryPerspectiveNote.user_id == user_id)
        .where(MemoryPerspectiveNote.status.in_(ACTIVE_NOTE_STATUSES))
        .order_by(MemoryPerspectiveNote.surface_after_at.asc())
        .limit(limit)
    )
    if not include_future:
        query = query.where(MemoryPerspectiveNote.surface_after_at <= utc_now())

    notes = list(db.scalars(query).all())
    return PerspectiveNoteListResponse(
        count=len(notes),
        notes=[_note_response(db=db, note=note) for note in notes],
    )


def mark_perspective_note_dismissed(
    *,
    db: Session,
    note_id: str,
    user_id: str | None,
) -> PerspectiveNoteDecisionResponse:
    note = _get_note_for_user(db=db, note_id=note_id, user_id=user_id)
    note.status = "dismissed"
    note.dismissed_at = utc_now()
    db.flush()
    return PerspectiveNoteDecisionResponse(
        id=note.id,
        status=note.status,
        decided_at=note.dismissed_at,
        next_step="Crowscap will stop surfacing this perspective note.",
    )


def mark_perspective_note_accepted(
    *,
    db: Session,
    note_id: str,
    user_id: str | None,
) -> PerspectiveNoteDecisionResponse:
    note = _get_note_for_user(db=db, note_id=note_id, user_id=user_id)
    note.status = "accepted"
    note.accepted_at = utc_now()
    db.flush()
    return PerspectiveNoteDecisionResponse(
        id=note.id,
        status=note.status,
        decided_at=note.accepted_at,
        next_step="Crowscap marked this as useful. A future step can convert accepted perspectives into new memories.",
    )


def _should_queue_perspective(memory: Memory) -> bool:
    if memory.status != "active":
        return False
    if memory.memory_type not in ELIGIBLE_MEMORY_TYPES:
        return False
    if memory.confidence == "high" and memory.source_strength == "strong":
        return False
    if memory.epistemic_label in ONE_SIDED_LABELS:
        return True
    return memory.confidence in {"medium", "low", "unknown"} or memory.source_strength in {"moderate", "weak", "unknown"}


def _has_active_note(*, db: Session, memory_id: str) -> bool:
    query = (
        select(MemoryPerspectiveNote.id)
        .where(MemoryPerspectiveNote.memory_id == memory_id)
        .where(MemoryPerspectiveNote.status.in_(ACTIVE_NOTE_STATUSES))
        .limit(1)
    )
    return db.scalar(query) is not None


def _perspective_type(memory: Memory) -> str:
    if memory.source_strength in {"weak", "unknown"}:
        return "evidence_gap"
    if memory.epistemic_label in {"opinion", "advice"}:
        return "nuance"
    return "counterpoint"


def _title_for(memory: Memory) -> str:
    if _perspective_type(memory) == "evidence_gap":
        return "Look for stronger evidence"
    if _perspective_type(memory) == "nuance":
        return "Consider where this may not apply"
    return "Look for a serious counterpoint"


def _content_for(memory: Memory) -> str:
    return (
        "You saved this idea, but Crowscap should not treat it as settled truth yet. "
        "When it resurfaces, compare it against a credible counterexample, boundary condition, "
        "or stronger source before deciding whether to keep, refine, or replace the belief."
    )


def _suggested_query_for(memory: Memory) -> str:
    trimmed = " ".join(memory.content.split())[:180]
    return f"{trimmed} counterarguments evidence limitations"


def _get_note_for_user(*, db: Session, note_id: str, user_id: str | None) -> MemoryPerspectiveNote:
    query = select(MemoryPerspectiveNote).where(MemoryPerspectiveNote.id == note_id)
    query = query.where(MemoryPerspectiveNote.user_id.is_(None) if user_id is None else MemoryPerspectiveNote.user_id == user_id)
    note = db.scalar(query)
    if note is None:
        raise LookupError("Perspective note not found.")
    return note


def _note_response(*, db: Session, note: MemoryPerspectiveNote) -> PerspectiveNoteResponse:
    memory = db.get(Memory, note.memory_id)
    source_title = memory.source.title if memory is not None and memory.source is not None else None
    return PerspectiveNoteResponse(
        id=note.id,
        memory_id=note.memory_id,
        memory_content=memory.content if memory is not None else "",
        source_title=source_title,
        status=note.status,
        perspective_type=note.perspective_type,
        title=note.title,
        content=note.content,
        suggested_query=note.suggested_query,
        confidence=note.confidence,
        surface_after_at=note.surface_after_at,
        created_at=note.created_at,
    )
