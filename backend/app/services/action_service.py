from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActionItem, Memory, Source, utc_now
from app.schemas.action import (
    ActionItemResponse,
    ActionListResponse,
    ActionSuggestionListResponse,
    ActionSuggestionResponse,
    CreateActionFromMemoryRequest,
    UpdateActionItemRequest,
)


def list_actions(
    *,
    db: Session,
    status: str | None = None,
    limit: int = 50,
    user_id: str | None = None,
) -> ActionListResponse:
    query = select(ActionItem).order_by(ActionItem.created_at.desc()).limit(limit)
    if user_id is None:
        query = query.where(ActionItem.user_id.is_(None))
    else:
        query = query.where(ActionItem.user_id == user_id)
    if status:
        query = query.where(ActionItem.status == status)

    actions = [_action_response(action) for action in db.scalars(query).all()]
    return ActionListResponse(count=len(actions), actions=actions)


def list_action_suggestions(
    *,
    db: Session,
    limit: int = 20,
    user_id: str | None = None,
) -> ActionSuggestionListResponse:
    action_query = select(ActionItem.memory_id).where(ActionItem.memory_id.is_not(None))
    if user_id is None:
        action_query = action_query.where(ActionItem.user_id.is_(None))
    else:
        action_query = action_query.where(ActionItem.user_id == user_id)
    existing_memory_ids = {
        memory_id for memory_id in db.scalars(action_query).all() if memory_id is not None
    }
    query = (
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.status == "active")
        .where(Memory.memory_type == "action")
        .order_by(Memory.created_at.desc())
    )
    if user_id is None:
        query = query.where(Memory.user_id.is_(None))
    else:
        query = query.where(Memory.user_id == user_id)

    suggestions: list[ActionSuggestionResponse] = []
    for memory, source in db.execute(query).all():
        if memory.id in existing_memory_ids:
            continue
        suggestions.append(
            ActionSuggestionResponse(
                memory_id=memory.id,
                source_id=source.id,
                source_title=source.title,
                memory_type=memory.memory_type,
                epistemic_label=memory.epistemic_label,
                content=memory.content,
                summary=memory.summary,
                confidence=memory.confidence,
                source_strength=memory.source_strength,
                suggested_title=_title_for_memory(memory),
            )
        )
        if len(suggestions) >= limit:
            break

    return ActionSuggestionListResponse(count=len(suggestions), suggestions=suggestions)


def create_action_from_memory(
    *,
    db: Session,
    memory_id: str,
    payload: CreateActionFromMemoryRequest,
    user_id: str | None = None,
) -> ActionItemResponse:
    memory = db.get(Memory, memory_id)
    if memory is None:
        raise LookupError("Memory not found.")
    if user_id is not None and memory.user_id != user_id:
        raise LookupError("Memory not found.")

    existing_query = select(ActionItem).where(ActionItem.memory_id == memory.id).limit(1)
    if user_id is None:
        existing_query = existing_query.where(ActionItem.user_id.is_(None))
    else:
        existing_query = existing_query.where(ActionItem.user_id == user_id)
    existing = db.scalars(existing_query).first()
    if existing is not None:
        return _action_response(existing)

    action = ActionItem(
        user_id=memory.user_id,
        memory_id=memory.id,
        source_id=memory.source_id,
        title=payload.title or _title_for_memory(memory),
        description=payload.description or memory.content,
        status=payload.status,
        due_at=payload.due_at,
        completed_at=utc_now() if payload.status == "done" else None,
        created_from="memory",
        metadata_json={
            "memory_type": memory.memory_type,
            "confidence": memory.confidence,
            "source_strength": memory.source_strength,
        },
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return _action_response(action)


def update_action_item(
    *,
    db: Session,
    action_id: str,
    payload: UpdateActionItemRequest,
    user_id: str | None = None,
) -> ActionItemResponse:
    action = db.get(ActionItem, action_id)
    if action is None:
        raise LookupError("Action item not found.")
    if user_id is not None and action.user_id != user_id:
        raise LookupError("Action item not found.")

    if payload.title is not None:
        action.title = payload.title
    if payload.description is not None:
        action.description = payload.description
    if payload.due_at is not None:
        action.due_at = payload.due_at
    if payload.status is not None:
        action.status = payload.status
        if payload.status == "done" and action.completed_at is None:
            action.completed_at = utc_now()
        if payload.status != "done":
            action.completed_at = None

    db.commit()
    db.refresh(action)
    return _action_response(action)


def _title_for_memory(memory: Memory) -> str:
    base = memory.summary or memory.content
    return base.strip()[:200]


def _action_response(action: ActionItem) -> ActionItemResponse:
    return ActionItemResponse(
        id=action.id,
        memory_id=action.memory_id,
        source_id=action.source_id,
        title=action.title,
        description=action.description,
        status=action.status,
        due_at=action.due_at,
        completed_at=action.completed_at,
        created_from=action.created_from,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )
