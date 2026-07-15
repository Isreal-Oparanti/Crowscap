from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


AnswerStyle = Literal["concise", "balanced", "detailed"]
EvidenceStrictness = Literal["relaxed", "balanced", "strict"]
ChallengeStyle = Literal["gentle", "balanced", "direct"]
MemoryDensity = Literal["compact", "balanced", "rich"]
RecallFrequency = Literal["low", "normal", "high", "daily", "weekly"]


class UserPreferenceResponse(BaseModel):
    id: str
    user_id: str | None = None
    preferred_review_time: str | None = None
    recall_frequency: RecallFrequency | None = None
    answer_style: AnswerStyle | None = None
    evidence_strictness: EvidenceStrictness = "balanced"
    challenge_style: ChallengeStyle = "balanced"
    memory_density: MemoryDensity | None = None
    notification_preference: str | None = None
    topics_of_interest: list[str] = Field(default_factory=list)
    source_preferences: dict = Field(default_factory=dict)
    updated_from_message_id: str | None = None
    updated_at: str


class UserPreferenceLearningResponse(BaseModel):
    preferences: UserPreferenceResponse
    updates: list[str] = Field(default_factory=list)
