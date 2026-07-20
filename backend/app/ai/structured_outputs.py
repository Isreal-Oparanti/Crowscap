from typing import Literal, get_args

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

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
    "compare",
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
ChatAction = Literal[
    "acknowledge",
    "conversation",
    "capture",
    "answer",
    "audit",
    "forget",
    "reminder",
    "self",
]
RecallRating = Literal["needs_work", "partial", "solid", "strong"]

# Derived from the EpistemicLabel Literal so this set never drifts out of sync.
EPISTEMIC_LABEL_VALUES: frozenset[str] = frozenset(get_args(EpistemicLabel))


def normalize_label(value: object) -> object:
    if not isinstance(value, str):
        return value
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def normalize_intent_label(value: object) -> object:
    normalized = normalize_label(value)
    aliases = {
        "comparison": "compare",
        "compare_with_existing": "compare",
        "compare_with_saved": "compare",
    }
    return aliases.get(normalized, normalized) if isinstance(normalized, str) else normalized


def normalize_memory_type_label(value: object) -> object:
    normalized = normalize_label(value)
    aliases = {
        "factual_claim": "claim",
        "personal_reflection": "claim",
        "source_summary": "reference",
    }
    return aliases.get(normalized, normalized) if isinstance(normalized, str) else normalized


def normalize_epistemic_label(value: object) -> object:
    normalized = normalize_label(value)
    aliases = {
        "fact": "factual_claim",
        "factual": "factual_claim",
        "claim": "factual_claim",
        "principle": "framework",
        "definition": "framework",
        "example": "anecdote",
        "warning": "advice",
        "action": "advice",
        "question": "unresolved",
        "quote": "source_summary",
        "reference": "source_summary",
        "summary": "source_summary",
        "intention": "personal_reflection",
        "intent": "personal_reflection",
    }
    return aliases.get(normalized, normalized) if isinstance(normalized, str) else normalized


def normalize_relationship_type_label(value: object) -> object:
    normalized = normalize_label(value)
    aliases = {
        "supports": "confirms",
        "support": "confirms",
        "contradicts": "conflicts",
        "contradiction": "conflicts",
        "depends_on_context": "tension",
        "context_dependent": "tension",
        "contextual_tension": "tension",
    }
    return aliases.get(normalized, normalized) if isinstance(normalized, str) else normalized


class ExtractedMemoryAtom(BaseModel):
    memory_type: MemoryType
    epistemic_label: EpistemicLabel
    content: str = Field(min_length=8, max_length=1200)
    summary: str | None = Field(default=None, max_length=300)
    confidence: Confidence
    confidence_reason: str = Field(min_length=8, max_length=500)
    source_strength: SourceStrength

    @model_validator(mode="before")
    @classmethod
    def repair_cross_field_taxonomy(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        repaired = dict(value)
        epistemic_label = normalize_epistemic_label(repaired.get("epistemic_label"))
        if isinstance(epistemic_label, str) and epistemic_label in EPISTEMIC_LABEL_VALUES:
            repaired["epistemic_label"] = epistemic_label
        return repaired

    @field_validator("memory_type", "epistemic_label", "confidence", "source_strength", mode="before")
    @classmethod
    def normalize_atom_labels(cls, value: object, info: ValidationInfo) -> object:
        if info.field_name == "memory_type":
            return normalize_memory_type_label(value)
        if info.field_name == "epistemic_label":
            return normalize_epistemic_label(value)
        return normalize_label(value)


class CaptureExtraction(BaseModel):
    source_title: str | None = Field(default=None, max_length=200)
    inferred_intents: list[CaptureIntent] = Field(default_factory=list, max_length=5)
    memories: list[ExtractedMemoryAtom] = Field(min_length=1, max_length=12)

    @field_validator("inferred_intents", mode="before")
    @classmethod
    def normalize_intents(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        return [normalize_intent_label(item) for item in value]


class MemoryRelationshipAssessment(BaseModel):
    source_memory_id: str = Field(min_length=1, max_length=80)
    related_memory_id: str = Field(min_length=1, max_length=80)
    relationship_type: MemoryRelationType
    strength: RelationStrength = "unknown"
    evidence_from_source: str = Field(min_length=2, max_length=300)
    evidence_from_related: str = Field(min_length=2, max_length=300)
    explanation: str = Field(min_length=8, max_length=500)

    @field_validator("relationship_type", "strength", mode="before")
    @classmethod
    def normalize_relation_labels(cls, value: object, info: ValidationInfo) -> object:
        if info.field_name == "relationship_type":
            return normalize_relationship_type_label(value)
        return normalize_label(value)


class MemoryRelationshipBatch(BaseModel):
    relationships: list[MemoryRelationshipAssessment] = Field(default_factory=list, max_length=60)


class ChatRoute(BaseModel):
    action: ChatAction
    reply: str | None = Field(default=None, max_length=500)
    reason: str = Field(min_length=3, max_length=300)

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: object) -> object:
        normalized = normalize_label(value)
        aliases = {
            "converse": "acknowledge",
            "chat": "acknowledge",
            "save": "capture",
            "remember": "capture",
            "query": "answer",
            "question": "answer",
            "search": "answer",
            "belief_check": "audit",
            "belief_audit": "audit",
            "evidence_check": "audit",
            "challenge": "audit",
            "archive": "forget",
            "forget_memory": "forget",
            "remind": "reminder",
            "schedule": "reminder",
            "capability": "self",
            "capabilities": "self",
            "identity": "self",
            "self_knowledge": "self",
        }
        return aliases.get(normalized, normalized) if isinstance(normalized, str) else normalized


class GroundedChatSynthesis(BaseModel):
    answer: str = Field(min_length=8, max_length=4000)
    knowledge_gaps: list[str] = Field(default_factory=list, max_length=5)
    tensions: list[str] = Field(default_factory=list, max_length=5)
    next_step: str | None = Field(default=None, max_length=500)


class BeliefAuditSynthesis(BaseModel):
    answer: str = Field(min_length=8, max_length=5000)
    current_understanding: str = Field(min_length=8, max_length=1600)
    strongest_saved_ideas: list[str] = Field(default_factory=list, max_length=6)
    public_evidence_summary: str = Field(min_length=8, max_length=1600)
    unsupported_or_weak_points: list[str] = Field(default_factory=list, max_length=6)
    ideas_to_compare: list[str] = Field(default_factory=list, max_length=6)
    confidence: Confidence
    confidence_reason: str = Field(min_length=8, max_length=800)
    next_questions: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: object) -> object:
        return normalize_label(value)


class ConversationalChatReply(BaseModel):
    reply: str = Field(min_length=2, max_length=3000)


class RecallEvaluation(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    rating: RecallRating
    feedback: str = Field(min_length=8, max_length=1200)
    understanding_summary: str = Field(min_length=8, max_length=1200)
    knowledge_gaps: list[str] = Field(default_factory=list, max_length=6)
    context_to_consider: list[str] = Field(default_factory=list, max_length=6)
    next_question: str | None = Field(default=None, max_length=500)

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_rating(cls, value: object) -> object:
        normalized = normalize_label(value)
        aliases = {
            "weak": "needs_work",
            "developing": "partial",
            "good": "solid",
            "excellent": "strong",
        }
        return aliases.get(normalized, normalized) if isinstance(normalized, str) else normalized
