from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.ai.structured_outputs import ChatAction
from app.schemas.belief import BeliefAuditResponse
from app.schemas.capture import TextCaptureResponse
from app.schemas.preference import UserPreferenceResponse
from app.schemas.reminder import ReminderResponse
from app.schemas.search import SearchResult


MAX_HISTORY_TURN_CHARS = 4000
MAX_HISTORY_TURNS = 12
MAX_CHAT_MESSAGE_CHARS = 40_000


class ConversationTurn(BaseModel):
    """A single prior turn sent by the client for context.

    History is advisory context, never authoritative data (the server prefers
    its own persisted history). Oversized turns are truncated instead of
    rejected: a hard max_length here once made every request in a conversation
    fail validation forever after one long paste entered the history.
    """

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)

    @field_validator("content", mode="after")
    @classmethod
    def _truncate_content(cls, value: str) -> str:
        return value[:MAX_HISTORY_TURN_CHARS]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_CHAT_MESSAGE_CHARS)
    conversation_id: str | None = None
    history: list[ConversationTurn] = Field(default_factory=list)

    @field_validator("history", mode="after")
    @classmethod
    def _limit_history(cls, value: list[ConversationTurn]) -> list[ConversationTurn]:
        return value[-MAX_HISTORY_TURNS:]


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
