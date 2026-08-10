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
        title="Identity and Purpose",
        body=(
            "I'm Crowscap, your personal memory intelligence system. I am built to help you turn scattered learning fragments "
            "into source-aware knowledge you can remember, question, compare, and actually use when it matters."
        ),
        keywords=("what", "who", "identity", "crowscap", "you", "are", "assistant", "purpose", "about"),
    ),
    SelfKnowledgeChunk(
        title="Problem and Thesis",
        body=(
            "People save useful articles, videos, books, and ideas to Notion, WhatsApp, or bookmarks, but almost never return to them. "
            "That creates a graveyard of forgotten links. Over time, people confuse false familiarity (having seen an idea before) with true understanding "
            "(being able to recall and defend it in a decision). Crowscap closes the gap between consuming information and actually knowing it."
        ),
        keywords=("problem", "thesis", "why", "exist", "built", "graveyard", "familiarity", "understanding", "learn", "losing"),
    ),
    SelfKnowledgeChunk(
        title="Product Experience and Lifecycle",
        body=(
            "Every piece of content you share moves through a simple lifecycle: "
            "1. Capture: You save text, URLs, YouTube videos, PDFs, or thoughts in chat without breaking your flow, preserving your original source and intent. "
            "2. Atomic Memory Cards: Content is separated into distinct, self-contained memory cards (principles, claims, actions, warnings, intentions, references). "
            "3. Meaning Search: Find saved memories by concept or meaning, not exact keywords. "
            "4. Spaced Recalls: Important thoughts resurface on your Recall tab when timing matters. "
            "5. Belief Audits: Inspect supporting evidence and missing context across your saved ideas."
        ),
        keywords=("how", "works", "work", "lifecycle", "product", "experience", "built", "cards", "atomic", "flow"),
    ),
    SelfKnowledgeChunk(
        title="Recall Engine and Timing",
        body=(
            "Recalls in Crowscap are scheduled resurfacing check-ins based on spaced repetition. "
            "When you save a link, video, or intention, Crowscap schedules an initial check-in within 24 to 72 hours. "
            "For learned principles, claims, and ideas, recalls recur at expanding intervals (1 day, 3 days, 7 days, 14 days, 30 days). "
            "Recalls appear on your Recall tab and as notification check-ins, surfacing one useful thought at a time with a prompt to help you review or act."
        ),
        keywords=("recall", "recalls", "timing", "when", "start", "schedule", "spaced", "repetition", "interval", "decay", "nudge", "happen", "getting"),
    ),
    SelfKnowledgeChunk(
        title="Belief Audit",
        body=(
            "A Belief Audit synthesizes across your saved memories on a topic to highlight what evidence supports your perspective, "
            "point out weak links or missing context, and compare related ideas. It does not tell you what to believe, but exposes the full picture so you can decide."
        ),
        keywords=("audit", "belief", "truth", "evidence", "public", "reliable", "verify", "compare", "gaps"),
    ),
    SelfKnowledgeChunk(
        title="Intentions and References",
        body=(
            "When you save a source to watch or read later, Crowscap classifies it as an intention or reference memory. "
            "It preserves your stated reason for saving it and checks back in on the Recall tab to ask if it's still something you want to explore or apply."
        ),
        keywords=("intention", "intentions", "watch later", "read later", "reference", "later"),
    ),
    SelfKnowledgeChunk(
        title="Reminders and Timed Nudges",
        body=(
            "You can set a timed reminder in chat anytime by stating what to remember and when (for example: 'Remind me tomorrow at 9am to watch the YC video'). "
            "Crowscap schedules the timed notification and surfaces it on your Recall tab and via check-in nudges when due."
        ),
        keywords=("remind", "reminder", "reminders", "timer", "schedule", "nudge", "nudges", "time", "clock"),
    ),
    SelfKnowledgeChunk(
        title="Archiving and Privacy",
        body=(
            "Your memories are strictly private to your account. You can archive any memory at any time to remove it from active search, recall, and belief audits, "
            "while keeping your original source preserved."
        ),
        keywords=("forget", "archive", "limit", "limits", "privacy", "private", "security"),
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

