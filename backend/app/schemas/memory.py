from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ai.structured_outputs import Confidence, EpistemicLabel, MemoryType, SourceStrength

ArchiveReason = Literal[
    "user_dismissed",
    "not_useful",
    "duplicate",
    "stale",
    "weak_evidence",
    "superseded",
    "other",
]


class ArchiveMemoryRequest(BaseModel):
    reason: ArchiveReason = "user_dismissed"
    note: str | None = Field(default=None, max_length=1000)


class MemoryArchiveResponse(BaseModel):
    memory_id: str
    previous_status: str
    new_status: str
    reason: str
    note: str | None
    archived_at: datetime


class RestoreMemoryResponse(BaseModel):
    memory_id: str
    previous_status: str
    new_status: str
    restored_at: datetime
    next_review_at: datetime | None


class RecentMemoryResponse(BaseModel):
    memory_id: str
    source_id: str
    source_type: str
    source_title: str | None
    memory_type: MemoryType
    epistemic_label: EpistemicLabel | None
    content: str
    summary: str | None
    confidence: Confidence
    confidence_reason: str | None
    source_strength: SourceStrength
    created_at: datetime


class RecentMemoryListResponse(BaseModel):
    count: int
    limit: int
    offset: int
    has_more: bool
    memories: list[RecentMemoryResponse]


class ArchiveCandidateResponse(BaseModel):
    memory_id: str
    source_id: str
    source_title: str | None
    memory_type: MemoryType
    epistemic_label: EpistemicLabel | None
    content: str
    confidence: Confidence
    source_strength: SourceStrength
    review_count: int
    created_at: datetime
    reasons: list[str]
    candidate_score: float


class ArchiveCandidateListResponse(BaseModel):
    count: int
    candidates: list[ArchiveCandidateResponse]


class CompressionCandidateResponse(BaseModel):
    memory_id: str
    content: str
    source_title: str | None
    related_count: int
    related_memory_ids: list[str]
    reason: str


class CompressionCandidateListResponse(BaseModel):
    count: int
    candidates: list[CompressionCandidateResponse]
