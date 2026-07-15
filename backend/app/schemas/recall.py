from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ai.structured_outputs import Confidence, EpistemicLabel, MemoryRelationType, MemoryType, RelationStrength, SourceStrength


class RecallRelationshipResponse(BaseModel):
    related_memory_id: str
    related_memory_content: str
    relationship_type: MemoryRelationType
    strength: RelationStrength
    explanation: str | None
    direction: str = Field(description="outgoing when this memory created the edge, incoming when another memory points to it")


class DueRecallMemoryResponse(BaseModel):
    memory_id: str
    source_id: str
    source_title: str | None
    memory_type: MemoryType
    epistemic_label: EpistemicLabel | None
    content: str
    summary: str | None
    confidence: Confidence
    confidence_reason: str | None
    source_strength: SourceStrength
    next_review_at: datetime
    last_reviewed_at: datetime | None
    review_count: int
    recall_score: float
    overdue_seconds: int
    recall_prompt: str
    epistemic_caution: str | None = None
    relationships: list[RecallRelationshipResponse] = Field(default_factory=list)


class DueReminderResponse(BaseModel):
    reminder_id: str
    content: str
    due_at: datetime
    overdue_seconds: int
    save_as_memory: bool
    memory_id: str | None = None
    status: str


class DueRecallsResponse(BaseModel):
    due_count: int
    now: datetime
    memories: list[DueRecallMemoryResponse]
    reminders: list[DueReminderResponse] = Field(default_factory=list)


class RecallAnswerRequest(BaseModel):
    answer: str = Field(min_length=3, max_length=5000)
    self_rating: int | None = Field(default=None, ge=1, le=4)


RecallQuickAction = Literal["still_relevant", "applied", "not_now"]


class RecallQuickRequest(BaseModel):
    action: RecallQuickAction


class RecallQuickResponse(BaseModel):
    memory_id: str
    action: RecallQuickAction
    feedback: str
    next_due_at: datetime
    review_count: int
    recall_score: float


class RecallAnswerResponse(BaseModel):
    review_id: str
    memory_id: str
    feedback: str
    score: float
    rating: str
    understanding_summary: str
    knowledge_gaps: list[str] = Field(default_factory=list)
    context_to_consider: list[str] = Field(default_factory=list)
    next_question: str | None
    next_due_at: datetime
    review_count: int
    recall_score: float
