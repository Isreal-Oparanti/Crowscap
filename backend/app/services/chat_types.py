"""Crowscap chat service — types, protocols, and AI implementations.

Extracted from chat_service.py.  This module owns:
  - Dataclasses: ReminderIntent, RecentCaptureContext, SelfKnowledgeChunk
  - Error classes: ChatRoutingError, ChatSynthesisError
  - Protocol interfaces: ChatIntentRouter, ChatSynthesizer, ChatConversationResponder
  - Qwen implementations of each protocol
  - Factory functions: get_chat_router, get_chat_synthesizer, get_chat_conversation_responder
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import ChatRoute, ConversationalChatReply, GroundedChatSynthesis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Capture, Memory, Source, UserPreference
from app.schemas.chat import ConversationTurn
from app.schemas.search import SearchResponse
from app.services.preference_service import format_preference_context
from app.services.chat_prompts import (
    CHAT_ROUTER_SYSTEM_PROMPT,
    CHAT_SYNTHESIS_SYSTEM_PROMPT,
    CHAT_CONVERSATION_SYSTEM_PROMPT,
    _build_router_prompt,
    _build_synthesis_prompt,
    _build_conversation_prompt,
)
from typing import Protocol

logger = get_logger("services.chat.types")

@dataclass(frozen=True)
class ReminderIntent:
    due_at: datetime
    content: str
    save_as_memory: bool
    time_phrase: str


@dataclass(frozen=True)
class RecentCaptureContext:
    capture: Capture
    source: Source
    memories: list[Memory]


@dataclass(frozen=True)
class SelfKnowledgeChunk:
    title: str
    body: str
    keywords: tuple[str, ...]


CROWSCAP_SELF_KNOWLEDGE: tuple[SelfKnowledgeChunk, ...] = (
    SelfKnowledgeChunk(
        title="Identity",
        body=(
            "Crowscap is a conversational memory intelligence system. It is built to help "
            "people turn learning fragments into source-aware knowledge they can remember, "
            "question, compare, and use."
        ),
        keywords=("what", "who", "identity", "crowscap", "you", "are", "assistant"),
    ),
    SelfKnowledgeChunk(
        title="Memory engine",
        body=(
            "Crowscap can capture text, URLs, YouTube transcripts, and PDFs; extract atomic "
            "memory cards; preserve the original source; create embeddings; search by meaning; "
            "and relate new ideas to older ideas."
        ),
        keywords=("memory", "capture", "source", "extract", "search", "youtube", "pdf", "url"),
    ),
    SelfKnowledgeChunk(
        title="Recall and reminders",
        body=(
            "Crowscap can schedule saved memories for recall. It can also create plain reminders "
            "without saving the reminder text as long-term semantic memory when the user asks for "
            "a practical nudge rather than knowledge storage."
        ),
        keywords=("recall", "remind", "reminder", "schedule", "notification", "forgetting"),
    ),
    SelfKnowledgeChunk(
        title="Belief audit",
        body=(
            "Crowscap can audit a topic by combining the user's saved memories, stored idea "
            "relationships, and public source leads. It is not a truth oracle; it should expose "
            "evidence strength, uncertainty, missing context, and ideas worth comparing."
        ),
        keywords=("audit", "belief", "truth", "evidence", "public", "reliable", "verify"),
    ),
    SelfKnowledgeChunk(
        title="Forgetting and limits",
        body=(
            "Crowscap can archive memories so they stop appearing in active search, recall, audits, "
            "and nearby context. It currently surfaces reminders inside the app; native push "
            "notifications, passive ambient capture, and full social-platform integrations are not "
            "complete yet."
        ),
        keywords=("forget", "archive", "limit", "limits", "cannot", "can't", "can", "push"),
    ),
)


class ChatRoutingError(RuntimeError):
    """Raised when a chat message cannot be classified safely."""


class ChatSynthesisError(RuntimeError):
    """Raised when memory-grounded chat output fails validation."""


class ChatIntentRouter(Protocol):
    def route(self, *, message: str, history: list[ConversationTurn]) -> ChatRoute:
        pass


class ChatSynthesizer(Protocol):
    def synthesize(
        self,
        *,
        question: str,
        history: list[ConversationTurn],
        search: SearchResponse,
        relation_context: list[str],
        preferences: UserPreference | None = None,
    ) -> GroundedChatSynthesis:
        pass


class ChatConversationResponder(Protocol):
    def respond(
        self,
        *,
        message: str,
        history: list[ConversationTurn],
        preferences: UserPreference | None = None,
    ) -> str:
        pass

