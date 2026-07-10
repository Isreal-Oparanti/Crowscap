from pydantic import BaseModel, Field, field_validator

from app.ai.structured_outputs import (
    CaptureIntent,
    Confidence,
    EpistemicLabel,
    MemoryRelationType,
    MemoryType,
    RelationStrength,
    SourceStrength,
)

TEXT_CAPTURE_CONTENT_MAX_LENGTH = 10_000
TEXT_CAPTURE_INTENT_MAX_LENGTH = 500
TEXT_CAPTURE_NOTE_MAX_LENGTH = 1_000
TEXT_CAPTURE_TITLE_MAX_LENGTH = 200


class TextCaptureRequest(BaseModel):
    content: str = Field(
        min_length=20,
        max_length=TEXT_CAPTURE_CONTENT_MAX_LENGTH,
        description=(
            "Captured text to extract. Longer content should use the future document upload "
            "pipeline so it can be chunked safely."
        ),
    )
    user_note: str | None = Field(default=None, max_length=TEXT_CAPTURE_NOTE_MAX_LENGTH)
    intent_text: str | None = Field(default=None, max_length=TEXT_CAPTURE_INTENT_MAX_LENGTH)
    source_title: str | None = Field(default=None, max_length=TEXT_CAPTURE_TITLE_MAX_LENGTH)

    @field_validator("content")
    @classmethod
    def explain_content_limit(cls, value: str) -> str:
        if len(value) > TEXT_CAPTURE_CONTENT_MAX_LENGTH:
            raise ValueError(
                "Content exceeds 10,000 characters. For longer content, use the document "
                "upload endpoint once it is available."
            )
        return value


class UrlCaptureRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    user_note: str | None = Field(default=None, max_length=TEXT_CAPTURE_NOTE_MAX_LENGTH)
    intent_text: str | None = Field(default=None, max_length=TEXT_CAPTURE_INTENT_MAX_LENGTH)


class MemoryRelationshipResponse(BaseModel):
    related_memory_id: str
    relationship_type: MemoryRelationType
    strength: RelationStrength
    explanation: str | None


class MemoryCardResponse(BaseModel):
    id: str
    source_type: str
    memory_type: MemoryType
    epistemic_label: EpistemicLabel | None
    content: str
    summary: str | None
    confidence: Confidence
    confidence_reason: str | None
    source_strength: SourceStrength
    embedding_dimensions: int | None = None
    relationships: list[MemoryRelationshipResponse] = Field(default_factory=list)


class TextCaptureResponse(BaseModel):
    capture_id: str
    source_id: str
    source_type: str
    source_title: str | None
    original_content: str | None
    status: str
    inferred_intents: list[CaptureIntent]
    memories: list[MemoryCardResponse]
