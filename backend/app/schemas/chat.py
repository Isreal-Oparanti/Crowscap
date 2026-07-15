from typing import Literal

from pydantic import BaseModel, Field

from app.ai.structured_outputs import ChatAction
from app.schemas.belief import BeliefAuditResponse
from app.schemas.capture import TextCaptureResponse
from app.schemas.preference import UserPreferenceResponse
from app.schemas.reminder import ReminderResponse
from app.schemas.search import SearchResult


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: str | None = None
    history: list[ConversationTurn] = Field(default_factory=list, max_length=12)


class ChatResponse(BaseModel):
    action: ChatAction
    message: str
    conversation_id: str | None = None
    user_message_id: str | None = None
    assistant_message_id: str | None = None
    saved: bool = False
    capture: TextCaptureResponse | None = None
    evidence: list[SearchResult] = Field(default_factory=list)
    knowledge_gaps: list[str] = Field(default_factory=list)
    tensions: list[str] = Field(default_factory=list)
    next_step: str | None = None
    audit: BeliefAuditResponse | None = None
    reminder: ReminderResponse | None = None
    preference_updates: list[str] = Field(default_factory=list)
    preferences: UserPreferenceResponse | None = None


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    action: ChatAction | None = None
    metadata_json: dict | None = None
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    messages: list[ChatMessageResponse] = Field(default_factory=list)
