from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session
from pydantic import BaseModel
import re
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

from app.services.recall_service import _clean_title

router = APIRouter(tags=["memories"])


def fix_user_perspective(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\bThe user intends?\b", "You intend", text, flags=re.IGNORECASE)
    text = re.sub(r"\bThe user wants?\b", "You want", text, flags=re.IGNORECASE)
    text = re.sub(r"\bThe user plans?\b", "You plan", text, flags=re.IGNORECASE)
    text = re.sub(r"\bUser intends?\b", "You intend", text, flags=re.IGNORECASE)
    text = re.sub(r"\bUser wants?\b", "You want", text, flags=re.IGNORECASE)
    text = re.sub(r"\bUser plans?\b", "You plan", text, flags=re.IGNORECASE)
    return text


def _clean_human_summary(raw_summary: str | None, raw_content: str | None) -> str | None:
    text = (raw_summary or raw_content or "").strip()
    if not text:
        return None

    # Clean academic/compliance prefix phrases
    text = re.sub(
        r"^(assess applicability of the framework to|assess applicability of|complete, standardized|asterisked courses are)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    text = fix_user_perspective(text)

    if text and len(text) > 1:
        text = text[0].upper() + text[1:]
    return text


@router.get("/recent", response_model=RecentMemoryListResponse)
def recent_memories(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=5000),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> RecentMemoryListResponse:
    filters = [Memory.status == "active", Memory.user_id == current_user.id]
    rows = db.execute(
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(*filters)
        .order_by(Memory.created_at.desc(), Memory.id.desc())
    ).all()

    # Group items by canonical URL to merge instant reference bookmark and extracted article
    groups: list[list[tuple[Memory, Source]]] = []
    group_map: dict[str, int] = {}

    for memory, source in rows:
        url_key = (source.resolved_url or source.original_url or "").strip().rstrip("/").lower()
        if not url_key:
            url_key = f"source:{source.id}"

        if url_key not in group_map:
            group_map[url_key] = len(groups)
            groups.append([])
        groups[group_map[url_key]].append((memory, source))

    all_unique_memories: list[RecentMemoryResponse] = []
    for items in groups:
        # Prefer non-reference memory (extracted insights like youtube, article, claim) over reference bookmark
        non_ref = [item for item in items if item[0].memory_type != "reference"]
        chosen_memory, chosen_source = non_ref[0] if non_ref else items[0]

        all_unique_memories.append(
            RecentMemoryResponse(
                memory_id=chosen_memory.id,
                source_id=chosen_source.id,
                source_type=chosen_source.source_type,
                source_title=_clean_title(chosen_source.title) if chosen_source.title else None,
                memory_type=chosen_memory.memory_type,
                epistemic_label=chosen_memory.epistemic_label,
                content=chosen_memory.content,
                summary=_clean_human_summary(chosen_memory.summary, chosen_memory.content),
                confidence=chosen_memory.confidence,
                confidence_reason=chosen_memory.confidence_reason,
                source_strength=chosen_memory.source_strength,
                created_at=chosen_memory.created_at,
            )
        )

    paginated_memories = all_unique_memories[offset : offset + limit]
    has_more = len(all_unique_memories) > (offset + limit)

    return RecentMemoryListResponse(
        count=len(paginated_memories),
        limit=limit,
        offset=offset,
        has_more=has_more,
        memories=paginated_memories,
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

    source = db.get(Source, memory.source_id) if memory.source_id else None

    # Collect all related source IDs (by source_id directly or matching original_url / resolved_url)
    target_source_ids = set()
    if source:
        target_source_ids.add(source.id)
        url = source.resolved_url or source.original_url
        if url:
            matching_sources = db.scalars(
                select(Source.id).where(
                    Source.user_id == current_user.id,
                    or_(Source.resolved_url == url, Source.original_url == url),
                )
            ).all()
            for s_id in matching_sources:
                target_source_ids.add(s_id)

    # Collect all memory IDs attached to these sources
    all_memory_ids = set()
    if target_source_ids:
        attached_mems = db.scalars(
            select(Memory.id).where(
                Memory.user_id == current_user.id,
                Memory.source_id.in_(list(target_source_ids)),
            )
        ).all()
        for m_id in attached_mems:
            all_memory_ids.add(m_id)
    all_memory_ids.add(memory_id)

    mem_ids_list = list(all_memory_ids)

    # Clean up memory references
    db.execute(delete(RecallReview).where(RecallReview.memory_id.in_(mem_ids_list)))
    db.execute(delete(MemoryArchiveEvent).where(MemoryArchiveEvent.memory_id.in_(mem_ids_list)))
    db.execute(delete(MemoryPerspectiveNote).where(MemoryPerspectiveNote.memory_id.in_(mem_ids_list)))
    db.execute(
        delete(MemoryRelation).where(
            or_(
                MemoryRelation.source_memory_id.in_(mem_ids_list),
                MemoryRelation.target_memory_id.in_(mem_ids_list),
            )
        )
    )
    db.execute(update(Reminder).where(Reminder.memory_id.in_(mem_ids_list)).values(memory_id=None))
    db.execute(update(ActionItem).where(ActionItem.memory_id.in_(mem_ids_list)).values(memory_id=None))

    # Delete all memories attached to the item/link
    db.execute(delete(Memory).where(Memory.id.in_(mem_ids_list)))

    # Delete captures referencing target_source_ids
    if target_source_ids:
        db.execute(delete(Capture).where(Capture.source_id.in_(list(target_source_ids))))

    # Delete all related sources for this link
    if target_source_ids:
        db.execute(delete(Source).where(Source.id.in_(list(target_source_ids))))

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
