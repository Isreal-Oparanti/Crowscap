from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_current_user
from app.db.session import get_db
from app.schemas.memory import (
    ArchiveCandidateListResponse,
    ArchiveMemoryRequest,
    CompressionCandidateListResponse,
    MemoryArchiveResponse,
    RestoreMemoryResponse,
)
from app.services.memory_lifecycle_service import (
    archive_memory,
    list_archive_candidates,
    list_compression_candidates,
    restore_memory,
)

router = APIRouter(tags=["memories"])


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
