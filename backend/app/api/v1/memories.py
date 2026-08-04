from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.core.auth import CurrentUser, require_current_user
from app.db.models import (
    ActionItem,
    Memory,
    MemoryArchiveEvent,
    MemoryPerspectiveNote,
    MemoryRelation,
    RecallReview,
    Reminder,
    Source,
)
from app.db.session import get_db
from app.schemas.memory import (
    ArchiveCandidateListResponse,
    ArchiveMemoryRequest,
    CompressionCandidateListResponse,
    MemoryArchiveResponse,
    RecentMemoryListResponse,
    RecentMemoryResponse,
    RestoreMemoryResponse,
)
from app.schemas.perspective import PerspectiveNoteDecisionResponse, PerspectiveNoteListResponse


# ---- Inline schemas for memory detail (no circular import risk) ----

class MemoryRelationDetail(BaseModel):
    related_memory_id: str
    relationship_type: str
    strength: str
    explanation: str


class MemoryAtomDetail(BaseModel):
    id: str
    memory_type: str
    epistemic_label: Optional[str]
    content: str
    summary: Optional[str]
    confidence: str
    confidence_reason: Optional[str]
    source_strength: str
    relationships: List[MemoryRelationDetail]


class SourceMemoriesResponse(BaseModel):
    source_id: str
    source_title: Optional[str]
    source_type: str
    source_url: Optional[str]
    memories: List[MemoryAtomDetail]
from app.services.memory_lifecycle_service import (
    archive_memory,
    list_archive_candidates,
    list_compression_candidates,
    restore_memory,
)
from app.services.perspective_service import (
    list_due_perspective_notes,
    mark_perspective_note_accepted,
    mark_perspective_note_dismissed,
)

router = APIRouter(tags=["memories"])


@router.get("/recent", response_model=RecentMemoryListResponse)
def recent_memories(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=5000),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> RecentMemoryListResponse:
    filters = [Memory.status == "active", Memory.user_id == current_user.id]
    count = db.scalar(select(func.count(Memory.id)).where(*filters)) or 0
    rows = db.execute(
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(*filters)
        .order_by(Memory.created_at.desc(), Memory.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    memories = [
        RecentMemoryResponse(
            memory_id=memory.id,
            source_id=source.id,
            source_type=source.source_type,
            source_title=source.title,
            memory_type=memory.memory_type,
            epistemic_label=memory.epistemic_label,
            content=memory.content,
            summary=memory.summary,
            confidence=memory.confidence,
            confidence_reason=memory.confidence_reason,
            source_strength=memory.source_strength,
            created_at=memory.created_at,
        )
        for memory, source in rows
    ]
    return RecentMemoryListResponse(
        count=count,
        limit=limit,
        offset=offset,
        has_more=offset + len(memories) < count,
        memories=memories,
    )


@router.get("/perspective-notes/due", response_model=PerspectiveNoteListResponse)
def due_perspective_notes(
    limit: int = Query(default=10, ge=1, le=50),
    include_future: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> PerspectiveNoteListResponse:
    return list_due_perspective_notes(
        db=db,
        user_id=current_user.id,
        limit=limit,
        include_future=include_future,
    )


@router.post("/perspective-notes/{note_id}/accept", response_model=PerspectiveNoteDecisionResponse)
def accept_perspective_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> PerspectiveNoteDecisionResponse:
    try:
        response = mark_perspective_note_accepted(db=db, note_id=note_id, user_id=current_user.id)
        db.commit()
        return response
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/perspective-notes/{note_id}/dismiss", response_model=PerspectiveNoteDecisionResponse)
def dismiss_perspective_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> PerspectiveNoteDecisionResponse:
    try:
        response = mark_perspective_note_dismissed(db=db, note_id=note_id, user_id=current_user.id)
        db.commit()
        return response
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/by-source/{source_id}", response_model=SourceMemoriesResponse)
def memories_by_source(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> SourceMemoriesResponse:
    """Return all active memory atoms from a given source capture, with their relations."""
    source = db.scalar(
        select(Source).where(Source.id == source_id, Source.user_id == current_user.id)
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")

    rows = db.execute(
        select(Memory)
        .where(Memory.source_id == source_id, Memory.user_id == current_user.id)
        .order_by(Memory.created_at.asc(), Memory.id.asc())
    ).scalars().all()

    atoms: List[MemoryAtomDetail] = []
    for mem in rows:
        rels = db.execute(
            select(MemoryRelation).where(MemoryRelation.source_memory_id == mem.id)
        ).scalars().all()
        atoms.append(MemoryAtomDetail(
            id=mem.id,
            memory_type=mem.memory_type,
            epistemic_label=mem.epistemic_label,
            content=mem.content,
            summary=mem.summary,
            confidence=mem.confidence,
            confidence_reason=mem.confidence_reason,
            source_strength=mem.source_strength,
            relationships=[
                MemoryRelationDetail(
                    related_memory_id=r.target_memory_id,
                    relationship_type=r.relationship_type,
                    strength=r.strength,
                    explanation=r.explanation,
                )
                for r in rels
            ],
        ))

    return SourceMemoriesResponse(
        source_id=source.id,
        source_title=source.title,
        source_type=source.source_type,
        source_url=source.resolved_url or source.original_url,
        memories=atoms,
    )


@router.get("/{memory_id}", response_model=MemoryAtomDetail)
def get_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> MemoryAtomDetail:
    """Return a single memory atom by ID with its relations."""
    memory = db.scalar(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == current_user.id)
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found.")

    rels = db.execute(
        select(MemoryRelation).where(MemoryRelation.source_memory_id == memory_id)
    ).scalars().all()

    return MemoryAtomDetail(
        id=memory.id,
        memory_type=memory.memory_type,
        epistemic_label=memory.epistemic_label,
        content=memory.content,
        summary=memory.summary,
        confidence=memory.confidence,
        confidence_reason=memory.confidence_reason,
        source_strength=memory.source_strength,
        relationships=[
            MemoryRelationDetail(
                related_memory_id=r.target_memory_id,
                relationship_type=r.relationship_type,
                strength=r.strength,
                explanation=r.explanation,
            )
            for r in rels
        ],
    )


@router.post("/{memory_id}/archive", response_model=MemoryArchiveResponse)
def archive(
    memory_id: str,
    payload: ArchiveMemoryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> MemoryArchiveResponse:
    try:
        return archive_memory(db=db, memory_id=memory_id, payload=payload, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{memory_id}/restore", response_model=RestoreMemoryResponse)
def restore(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> RestoreMemoryResponse:
    try:
        return restore_memory(db=db, memory_id=memory_id, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{memory_id}", status_code=204)
def delete_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> Response:
    memory = db.scalar(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == current_user.id)
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found.")

    db.execute(delete(RecallReview).where(RecallReview.memory_id == memory_id))
    db.execute(delete(MemoryArchiveEvent).where(MemoryArchiveEvent.memory_id == memory_id))
    db.execute(delete(MemoryPerspectiveNote).where(MemoryPerspectiveNote.memory_id == memory_id))
    db.execute(
        delete(MemoryRelation).where(
            or_(
                MemoryRelation.source_memory_id == memory_id,
                MemoryRelation.target_memory_id == memory_id,
            )
        )
    )
    db.execute(update(Reminder).where(Reminder.memory_id == memory_id).values(memory_id=None))
    db.execute(update(ActionItem).where(ActionItem.memory_id == memory_id).values(memory_id=None))
    db.delete(memory)
    db.commit()
    return Response(status_code=204)


@router.get("/archive-candidates", response_model=ArchiveCandidateListResponse)
def archive_candidates(
    limit: int = Query(default=20, ge=1, le=100),
    min_age_days: int = Query(default=30, ge=0, le=3650),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ArchiveCandidateListResponse:
    return list_archive_candidates(
        db=db,
        limit=limit,
        min_age_days=min_age_days,
        user_id=current_user.id,
    )


@router.get("/compression-candidates", response_model=CompressionCandidateListResponse)
def compression_candidates(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> CompressionCandidateListResponse:
    return list_compression_candidates(db=db, limit=limit, user_id=current_user.id)
