from pydantic import BaseModel, Field

from app.ai.structured_outputs import Confidence, EpistemicLabel, MemoryType, SourceStrength


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(
        default=0.25,
        ge=-1.0,
        le=1.0,
        description="Minimum cosine similarity. This is model-dependent and tuned empirically.",
    )
    include_archived: bool = False


class SearchResult(BaseModel):
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
    similarity_score: float
    embedding_dimensions: int | None = None


class SearchResponse(BaseModel):
    query: str
    min_score: float
    candidate_count: int
    embedded_candidate_count: int
    returned_count: int
    top_score: float | None = None
    results: list[SearchResult]
