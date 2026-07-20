from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Memory, MemoryArchiveEvent, MemoryRelation, Source, utc_now
from app.schemas.memory import (
    ArchiveCandidateListResponse,
    ArchiveCandidateResponse,
    ArchiveMemoryRequest,
    CompressionCandidateListResponse,
    CompressionCandidateResponse,
    MemoryArchiveResponse,
    RestoreMemoryResponse,
)


def archive_memory(
    *,
    db: Session,
    memory_id: str,
    payload: ArchiveMemoryRequest,
    user_id: str | None = None,
) -> MemoryArchiveResponse:
    memory = _get_memory(db=db, memory_id=memory_id, user_id=user_id)
    previous_status = memory.status
    memory.status = "archived"
    memory.next_review_at = None

    event = MemoryArchiveEvent(
        user_id=memory.user_id,
        memory_id=memory.id,
        previous_status=previous_status,
        new_status=memory.status,
        reason=payload.reason,
        note=payload.note,
        created_by="user",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return MemoryArchiveResponse(
        memory_id=memory.id,
        previous_status=previous_status,
        new_status=memory.status,
        reason=event.reason,
        note=event.note,
        archived_at=event.created_at,
    )


def restore_memory(
    *,
    db: Session,
    memory_id: str,
    user_id: str | None = None,
) -> RestoreMemoryResponse:
    memory = _get_memory(db=db, memory_id=memory_id, user_id=user_id)
    previous_status = memory.status
    memory.status = "active"
    if memory.next_review_at is None:
        memory.next_review_at = utc_now()

    event = MemoryArchiveEvent(
        user_id=memory.user_id,
        memory_id=memory.id,
        previous_status=previous_status,
        new_status=memory.status,
        reason="restored",
        created_by="user",
    )
    db.add(event)
    db.commit()

    return RestoreMemoryResponse(
        memory_id=memory.id,
        previous_status=previous_status,
        new_status=memory.status,
        restored_at=utc_now(),
        next_review_at=memory.next_review_at,
    )


def list_archive_candidates(
    *,
    db: Session,
    limit: int = 20,
    min_age_days: int = 30,
    user_id: str | None = None,
) -> ArchiveCandidateListResponse:
    cutoff = utc_now() - timedelta(days=min_age_days)
    # Apply a DB-side cap so we never load all memories into Python for scoring.
    # The Python sort below will find the top-limit candidates from this window.
    DB_SCAN_WINDOW = max(limit * 10, 200)
    query = (
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.status == "active")
        .order_by(Memory.created_at.asc())
        .limit(DB_SCAN_WINDOW)
    )
    if user_id is None:
        query = query.where(Memory.user_id.is_(None))
    else:
        query = query.where(Memory.user_id == user_id)

    candidates: list[ArchiveCandidateResponse] = []
    for memory, source in db.execute(query).all():
        reasons, score = _archive_reasons(memory=memory, cutoff=cutoff)
        if not reasons:
            continue
        candidates.append(
            ArchiveCandidateResponse(
                memory_id=memory.id,
                source_id=source.id,
                source_title=source.title,
                memory_type=memory.memory_type,
                epistemic_label=memory.epistemic_label,
                content=memory.content,
                confidence=memory.confidence,
                source_strength=memory.source_strength,
                review_count=memory.review_count,
                created_at=memory.created_at,
                reasons=reasons,
                candidate_score=round(score, 3),
            )
        )

    candidates.sort(key=lambda candidate: candidate.candidate_score, reverse=True)
    return ArchiveCandidateListResponse(count=min(len(candidates), limit), candidates=candidates[:limit])


def list_compression_candidates(
    *,
    db: Session,
    limit: int = 20,
    user_id: str | None = None,
) -> CompressionCandidateListResponse:
    # Apply a DB-side cap to avoid loading all memories into Python.
    DB_SCAN_WINDOW = max(limit * 20, 500)
    memory_query = (
        select(Memory, Source)
        .where(Memory.status == "active")
        .limit(DB_SCAN_WINDOW)
    )
    if user_id is None:
        memory_query = memory_query.where(Memory.user_id.is_(None))
    else:
        memory_query = memory_query.where(Memory.user_id == user_id)

    memory_rows = db.execute(memory_query.join(Source, Memory.source_id == Source.id)).all()
    memories = {memory.id: (memory, source) for memory, source in memory_rows}
    if not memories:
        return CompressionCandidateListResponse(count=0, candidates=[])

    memory_ids = list(memories)
    relation_query = select(MemoryRelation).where(
        MemoryRelation.relation_type.in_(["confirms", "extends", "qualifies"]),
        or_(
            MemoryRelation.source_memory_id.in_(memory_ids),
            MemoryRelation.target_memory_id.in_(memory_ids),
        ),
    )
    relation_rows = db.scalars(relation_query).all()

    related_by_memory: dict[str, set[str]] = {memory_id: set() for memory_id in memories}
    for relation in relation_rows:
        if relation.source_memory_id in related_by_memory and relation.target_memory_id in memories:
            related_by_memory[relation.source_memory_id].add(relation.target_memory_id)
        if relation.target_memory_id in related_by_memory and relation.source_memory_id in memories:
            related_by_memory[relation.target_memory_id].add(relation.source_memory_id)

    candidates: list[CompressionCandidateResponse] = []
    for memory_id, related_ids in related_by_memory.items():
        if len(related_ids) < 2:
            continue
        memory, source = memories[memory_id]
        candidates.append(
            CompressionCandidateResponse(
                memory_id=memory.id,
                content=memory.content,
                source_title=source.title,
                related_count=len(related_ids),
                related_memory_ids=sorted(related_ids),
                reason=(
                    "This memory has multiple agreeing or extending memories. "
                    "It may be a future candidate for a user-approved compressed principle."
                ),
            )
        )

    candidates.sort(key=lambda candidate: candidate.related_count, reverse=True)
    return CompressionCandidateListResponse(
        count=min(len(candidates), limit),
        candidates=candidates[:limit],
    )


def _get_memory(*, db: Session, memory_id: str, user_id: str | None) -> Memory:
    memory = db.get(Memory, memory_id)
    if memory is None:
        raise LookupError("Memory not found.")
    if user_id is not None and memory.user_id != user_id:
        raise LookupError("Memory not found.")
    return memory


def _archive_reasons(*, memory: Memory, cutoff: datetime) -> tuple[list[str], float]:
    reasons: list[str] = []
    score = 0.0
    created_at = _ensure_aware(memory.created_at)

    if memory.confidence == "low":
        reasons.append("low confidence")
        score += 0.4
    elif memory.confidence == "unknown":
        reasons.append("unknown confidence")
        score += 0.25

    if memory.source_strength == "weak":
        reasons.append("weak source strength")
        score += 0.3
    elif memory.source_strength == "unknown":
        reasons.append("unknown source strength")
        score += 0.15

    if memory.review_count == 0 and created_at <= cutoff:
        reasons.append("never reviewed and older than the archive age threshold")
        score += 0.3

    if memory.epistemic_label in {"opinion", "anecdote", "prediction"} and memory.source_strength != "strong":
        reasons.append("context-dependent claim without strong source support")
        score += 0.2

    if memory.memory_type in {"intention", "reference"} and created_at <= cutoff:
        reasons.append("old meta memory that may no longer need active recall")
        score += 0.2

    if score < 0.4:
        return [], score
    return reasons, score


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=utc_now().tzinfo)
    return value
