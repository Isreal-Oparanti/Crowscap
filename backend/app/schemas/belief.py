from typing import Literal

from pydantic import BaseModel, Field

from app.ai.structured_outputs import Confidence
from app.schemas.search import SearchResult

PublicSearchStatus = Literal["searched", "no_results", "disabled", "failed"]


class BeliefAuditRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=240)
    include_public_evidence: bool = True
    public_query_count: int = Field(default=3, ge=0, le=4)
    public_results_per_query: int = Field(default=3, ge=1, le=5)
    memory_limit: int = Field(default=8, ge=1, le=15)


class PublicEvidenceResult(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=8, max_length=2048)
    snippet: str | None = Field(default=None, max_length=800)
    source: str | None = Field(default=None, max_length=160)
    query: str = Field(min_length=2, max_length=300)
    rank: int | None = Field(default=None, ge=1)


class BeliefAuditResponse(BaseModel):
    topic: str
    answer: str
    current_understanding: str
    strongest_saved_ideas: list[str] = Field(default_factory=list)
    public_evidence_summary: str
    unsupported_or_weak_points: list[str] = Field(default_factory=list)
    ideas_to_compare: list[str] = Field(default_factory=list)
    confidence: Confidence
    confidence_reason: str
    next_questions: list[str] = Field(default_factory=list)
    memories: list[SearchResult] = Field(default_factory=list)
    public_evidence: list[PublicEvidenceResult] = Field(default_factory=list)
    public_search_status: PublicSearchStatus
    public_search_message: str | None = None
