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
    source_id: str | None = Field(
        default=None,
        description=(
            "When set, bypass semantic ranking entirely and deterministically "
            "list every memory for this one source (newest first), up to "
            "`limit`. Use this for 'what did I save from that video/link' "
            "style questions, where the user wants the source's own content, "
            "not whatever happens to rank highest against their whole "
            "corpus for this query string. `query` is still required by this "
            "schema but is ignored on this path."
        ),
    )


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
