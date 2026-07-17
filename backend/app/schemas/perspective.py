from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PerspectiveStatus = Literal["queued", "surfaced", "accepted", "dismissed"]
PerspectiveType = Literal["counterpoint", "nuance", "evidence_gap"]


class PerspectiveNoteResponse(BaseModel):
    id: str
    memory_id: str
    memory_content: str
    source_title: str | None = None
    status: PerspectiveStatus
    perspective_type: PerspectiveType
    title: str
    content: str
    suggested_query: str | None = None
    confidence: str
    surface_after_at: datetime
    created_at: datetime


class PerspectiveNoteListResponse(BaseModel):
    count: int
    notes: list[PerspectiveNoteResponse] = Field(default_factory=list)


class PerspectiveNoteDecisionResponse(BaseModel):
    id: str
    status: PerspectiveStatus
    decided_at: datetime
    next_step: str
