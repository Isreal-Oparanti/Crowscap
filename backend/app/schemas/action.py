from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ai.structured_outputs import Confidence, EpistemicLabel, MemoryType, SourceStrength

ActionStatus = Literal["proposed", "planned", "doing", "done", "dismissed"]


class ActionItemResponse(BaseModel):
    id: str
    memory_id: str | None
    source_id: str | None
    title: str
    description: str | None
    status: ActionStatus | str
    due_at: datetime | None
    completed_at: datetime | None
    created_from: str
    created_at: datetime
    updated_at: datetime


class ActionSuggestionResponse(BaseModel):
    memory_id: str
    source_id: str
    source_title: str | None
    memory_type: MemoryType
    epistemic_label: EpistemicLabel | None
    content: str
    summary: str | None
    confidence: Confidence
    source_strength: SourceStrength
    suggested_title: str


class ActionListResponse(BaseModel):
    count: int
    actions: list[ActionItemResponse]


class ActionSuggestionListResponse(BaseModel):
    count: int
    suggestions: list[ActionSuggestionResponse]


class CreateActionFromMemoryRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: ActionStatus = "planned"
    due_at: datetime | None = None


class UpdateActionItemRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: ActionStatus | None = None
    due_at: datetime | None = None
