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
from app.db.models import Capture, ChatMessage, Memory, Source, UserPreference
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
class ResolvedChatContext:
    latest_user_message: ChatMessage | None
    latest_assistant_message: ChatMessage | None
    latest_capture: Capture | None
    latest_source: Source | None
    latest_memory_ids: list[str]
    pending_url: str | None
    declined_pending_urls: tuple[str, ...]
    recent_link: str | None
    recent_link_read_status: str | None
    recent_link_user_reason: str | None
    deictic_target_hint: str | None


@dataclass(frozen=True)
class SelfKnowledgeChunk:
    title: str
    body: str
    keywords: tuple[str, ...]


CROWSCAP_SELF_KNOWLEDGE: tuple[SelfKnowledgeChunk, ...] = (
    SelfKnowledgeChunk(
        title="Identity",
        body=(
            "I'm Crowscap, your personal memory intelligence system. I'm built to help "
            "you turn learning fragments into source-aware knowledge you can remember, "
            "question, compare, and use."
        ),
        keywords=("what", "who", "identity", "crowscap", "you", "are", "assistant"),
    ),
    SelfKnowledgeChunk(
        title="Memory engine",
        body=(
            "I can capture text, URLs, YouTube transcripts, and PDFs; extract atomic "
            "memory cards; preserve the original source; create embeddings; search by meaning; "
            "and relate new ideas to older ideas."
        ),
        keywords=("memory", "capture", "source", "extract", "search", "youtube", "pdf", "url"),
    ),
    SelfKnowledgeChunk(
        title="Recall engine and timing",
        body=(
            "Recalls in Crowscap are scheduled resurfacing check-ins for your saved memories based on spaced repetition. "
            "When you save a link, video, or intention, Crowscap schedules an initial check-in within 24 to 72 hours. "
            "For learned principles, claims, and ideas, recalls recur at expanding intervals (1 day, 3 days, 7 days, 14 days, 30 days). "
            "Recalls appear on your Recall tab and as notification check-ins, surfacing one useful thought at a time with a prompt to help you review or act."
        ),
        keywords=("recall", "recalls", "timing", "when", "start", "schedule", "spaced", "repetition", "interval", "decay", "nudge", "happen", "getting"),
    ),
    SelfKnowledgeChunk(
        title="Belief audit",
        body=(
            "I can audit a topic by combining your saved memories, stored idea "
            "relationships, and public source leads. I am not a truth oracle; I expose "
            "evidence strength, uncertainty, missing context, and ideas worth comparing."
        ),
        keywords=("audit", "belief", "truth", "evidence", "public", "reliable", "verify"),
    ),
    SelfKnowledgeChunk(
        title="Intentions and references",
        body=(
            "When you save a source to watch or read later, Crowscap classifies it as an intention or reference memory. "
            "It preserves your stated intent for saving it and checks back in on the Recall tab to ask if it's still something you want to explore or apply."
        ),
        keywords=("intention", "intentions", "watch later", "read later", "reference", "later"),
    ),
    SelfKnowledgeChunk(
        title="Forgetting and limits",
        body=(
            "I can archive memories so they stop appearing in active search, recall, audits, "
            "and nearby context. I currently surface reminders inside the app; native push "
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

