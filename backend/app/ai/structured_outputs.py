from typing import Literal

from pydantic import BaseModel, Field

CaptureIntent = Literal[
    "learned",
    "remember",
    "watch_later",
    "read_later",
    "verify",
    "apply",
    "reference",
    "inspiration",
    "disagree",
    "question",
]

MemoryType = Literal[
    "claim",
    "principle",
    "definition",
    "example",
    "warning",
    "action",
    "question",
    "quote",
    "reference",
    "intention",
]

EpistemicLabel = Literal[
    "factual_claim",
    "opinion",
    "advice",
    "anecdote",
    "prediction",
    "framework",
    "personal_reflection",
    "unresolved",
    "source_summary",
]

Confidence = Literal["low", "medium", "high", "unknown"]
SourceStrength = Literal["weak", "moderate", "strong", "unknown"]
MemoryRelationType = Literal["confirms", "conflicts", "tension", "extends", "qualifies", "unrelated"]
RelationStrength = Literal["weak", "moderate", "strong", "unknown"]


class ExtractedMemoryAtom(BaseModel):
    memory_type: MemoryType
    epistemic_label: EpistemicLabel
    content: str = Field(min_length=8, max_length=1200)
    summary: str | None = Field(default=None, max_length=300)
    confidence: Confidence
    confidence_reason: str = Field(min_length=8, max_length=500)
    source_strength: SourceStrength


class CaptureExtraction(BaseModel):
    source_title: str | None = Field(default=None, max_length=200)
    inferred_intents: list[CaptureIntent] = Field(default_factory=list, max_length=5)
    memories: list[ExtractedMemoryAtom] = Field(min_length=1, max_length=12)


class MemoryRelationshipAssessment(BaseModel):
    source_memory_id: str = Field(min_length=1, max_length=80)
    related_memory_id: str = Field(min_length=1, max_length=80)
    relationship_type: MemoryRelationType
    strength: RelationStrength = "unknown"
    explanation: str = Field(min_length=8, max_length=500)


class MemoryRelationshipBatch(BaseModel):
    relationships: list[MemoryRelationshipAssessment] = Field(default_factory=list, max_length=60)
