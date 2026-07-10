from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.action import (
    ActionItemResponse,
    ActionListResponse,
    ActionSuggestionListResponse,
    CreateActionFromMemoryRequest,
    UpdateActionItemRequest,
)
from app.services.action_service import (
    create_action_from_memory,
    list_action_suggestions,
    list_actions,
    update_action_item,
)

router = APIRouter(tags=["actions"])


@router.get("", response_model=ActionListResponse)
def actions(
    status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ActionListResponse:
    return list_actions(db=db, status=status, limit=limit)


@router.get("/suggestions", response_model=ActionSuggestionListResponse)
def action_suggestions(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ActionSuggestionListResponse:
    return list_action_suggestions(db=db, limit=limit)


@router.post("/from-memory/{memory_id}", response_model=ActionItemResponse)
def create_from_memory(
    memory_id: str,
    payload: CreateActionFromMemoryRequest,
    db: Session = Depends(get_db),
) -> ActionItemResponse:
    try:
        return create_action_from_memory(db=db, memory_id=memory_id, payload=payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{action_id}", response_model=ActionItemResponse)
def update_action(
    action_id: str,
    payload: UpdateActionItemRequest,
    db: Session = Depends(get_db),
) -> ActionItemResponse:
    try:
        return update_action_item(db=db, action_id=action_id, payload=payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
