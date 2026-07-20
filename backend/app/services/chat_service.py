from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Protocol
from urllib.parse import urlparse

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import ChatRoute, ConversationalChatReply, GroundedChatSynthesis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    Capture,
    ChatMessage,
    Conversation,
    Memory,
    MemoryArchiveEvent,
    MemoryRelation,
    Source,
    UserPreference,
    utc_now,
)
from app.db.vector import update_memory_embedding_vector
from app.schemas.belief import BeliefAuditRequest
from app.schemas.capture import (
    MemoryCardResponse,
    TextCaptureRequest,
    TextCaptureResponse,
    UrlCaptureRequest,
)
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ConversationTurn,
)
from app.schemas.memory import ArchiveMemoryRequest
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.belief_audit_service import BeliefAuditor
from app.services.capture_service import create_text_capture, initial_next_review_at
from app.services.embedding_service import MemoryEmbedder
from app.services.extraction_service import MemoryExtractor
from app.services.ingestion_service import (
    IngestionError,
    create_pdf_capture_from_bytes,
    create_url_capture,
    unsupported_url_reason,
)
from app.services.memory_lifecycle_service import archive_memory
from app.services.preference_service import (
    PreferenceLearningResult,
    format_preference_context,
    is_explicit_preference_statement,
    learn_preferences_from_message,
    maybe_autonomously_update_preferences,
    preference_response,
)
from app.services.relationship_service import MemoryRelationDetector
from app.services.reminder_service import create_reminder
from app.services.search_service import search_memories

logger = get_logger("services.chat")

MEMORY_QUERY_MIN_SCORE = 0.25
CONVERSATION_MEMORY_MIN_SCORE = 0.55
MIN_DIRECT_TEXT_CAPTURE_CHARS = 20
PROMPT_HISTORY_RECENT_TURNS = 6
PROMPT_HISTORY_SUMMARY_TRIGGER_TURNS = 10
MEMORY_CONTEXT_TOKEN_BUDGET = 2000
MEMORY_NEAR_DUPLICATE_RATIO = 0.82
SESSION_CONVERSATION_MARKERS = (
    "in this chat",
    "this chat",
    "this conversation",
    "current chat",
    "this session",
    "beginning of our chat",
    "beginning of this chat",
    "start of our chat",
    "start of this chat",
    "earlier here",
    "earlier in chat",
    "earlier in this chat",
    "have i thanked",
    "did i thank",
    "first thing i said",
    "very first thing",
    "first message",
    "first thing",
    "what did i just say",
    "what was my last message",
    "last message",
)


# Types, error classes, and Protocol interfaces live in chat_types for clarity.
# Qwen implementations remain here as they depend on private helpers in this module.
from app.services.chat_types import (
    ReminderIntent,
    RecentCaptureContext,
    SelfKnowledgeChunk,
    CROWSCAP_SELF_KNOWLEDGE,
    ChatRoutingError,
    ChatSynthesisError,
    ChatIntentRouter,
    ChatSynthesizer,
    ChatConversationResponder,
)


class QwenChatIntentRouter:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()
        self.settings = get_settings()

    def route(self, *, message: str, history: list[ConversationTurn]) -> ChatRoute:
        deterministic = _deterministic_route(message, history=history)
        if deterministic is not None:
            logger.info(
                "\U0001f9ed chat.route.deterministic action=%s chars=%s",
                deterministic.action,
                len(message),
            )
            return deterministic

        payload = self.client.chat_json(
            system_prompt=CHAT_ROUTER_SYSTEM_PROMPT,
            user_prompt=_build_router_prompt(message=message, history=history, pending_url=_pending_url_from_history(history)),
            model=self.settings.qwen_fast_model,
            temperature=0.0,
            timeout_seconds=15.0,
            max_retries=1,
        )
        try:
            route = ChatRoute.model_validate(payload)
        except ValidationError as exc:
            raise ChatRoutingError(f"Chat routing failed schema validation: {exc}") from exc

        logger.info("\U0001f9ed chat.route.model action=%s chars=%s", route.action, len(message))
        return route


class QwenChatSynthesizer:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()
        self.settings = get_settings()

    def synthesize(
        self,
        *,
        question: str,
        history: list[ConversationTurn],
        search: SearchResponse,
        relation_context: list[str],
        preferences: UserPreference | None = None,
    ) -> GroundedChatSynthesis:
        payload = self.client.chat_json(
            system_prompt=CHAT_SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=_build_synthesis_prompt(
                question=question,
                history=history,
                search=search,
                relation_context=relation_context,
                preference_context=format_preference_context(preferences),
            ),
            model=self.settings.qwen_chat_model,
            temperature=0.2,
        )
        try:
            return GroundedChatSynthesis.model_validate(payload)
        except ValidationError as exc:
            raise ChatSynthesisError(f"Chat synthesis failed schema validation: {exc}") from exc


class QwenChatConversationResponder:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()
        self.settings = get_settings()

    def respond(
        self,
        *,
        message: str,
        history: list[ConversationTurn],
        preferences: UserPreference | None = None,
    ) -> str:
        payload = self.client.chat_json(
            system_prompt=CHAT_CONVERSATION_SYSTEM_PROMPT,
            user_prompt=_build_conversation_prompt(
                message=message,
                history=history,
                preference_context=format_preference_context(preferences),
            ),
            model=self.settings.qwen_chat_model,
            temperature=0.35,
            timeout_seconds=30.0,
            max_retries=1,
        )
        try:
            reply = ConversationalChatReply.model_validate(payload)
        except ValidationError as exc:
            raise ChatSynthesisError(f"Conversation reply failed schema validation: {exc}") from exc
        return reply.reply


def get_chat_router() -> ChatIntentRouter:
    return QwenChatIntentRouter()


def get_chat_synthesizer() -> ChatSynthesizer:
    return QwenChatSynthesizer()


def get_chat_conversation_responder() -> ChatConversationResponder:
    return QwenChatConversationResponder()


def get_current_conversation(
    *,
    db: Session,
    user_id: str | None = None,
) -> ConversationResponse | None:
    query = (
        select(Conversation)
        .where(Conversation.status == "active")
        .where(Conversation.user_id.is_(None) if user_id is None else Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
    )
    conversation = db.scalars(query).first()
    return _conversation_response(conversation) if conversation is not None else None


def get_conversation(
    *,
    db: Session,
    conversation_id: str,
    user_id: str | None = None,
) -> ConversationResponse | None:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        return None
    if user_id is not None and conversation.user_id != user_id:
        return None
    return _conversation_response(conversation)


def process_chat_message(
    *,
    db: Session,
    payload: ChatRequest,
    router: ChatIntentRouter,
    synthesizer: ChatSynthesizer,
    conversation_responder: ChatConversationResponder,
    belief_auditor: BeliefAuditor,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_id: str | None = None,
) -> ChatResponse:
    conversation = _get_or_create_conversation(
        db=db,
        conversation_id=payload.conversation_id,
        first_message=payload.message,
        user_id=user_id,
    )
    persisted_history = _conversation_turns(conversation, limit=None)
    effective_history = persisted_history or payload.history
    pending_url = _pending_url_from_history(effective_history)
    grounded_local_reply = _grounded_local_conversation_reply(
        db=db,
        message=payload.message,
        history=effective_history,
        conversation=conversation,
        user_id=user_id,
    )

    logger.info(
        "\U0001f4ac chat.message.start chars=%s history=%s conversation_id=%s",
        len(payload.message),
        len(effective_history),
        conversation.id,
    )
    if grounded_local_reply is not None:
        route = ChatRoute(
            action="conversation",
            reply=grounded_local_reply,
            reason="The user is asking for a fact from the current conversation.",
        )
        logger.info("\U0001f9ed chat.route.grounded_local chars=%s", len(payload.message))
    else:
        route = router.route(message=payload.message, history=effective_history)
        route = _stabilize_route_for_local_context(
            route=route,
            message=payload.message,
            history=effective_history,
            pending_url=pending_url,
        )

    user_message = ChatMessage(
        conversation_id=conversation.id,
        user_id=user_id,
        role="user",
        content=payload.message,
    )
    db.add(user_message)
    db.flush()
    preference_learning = learn_preferences_from_message(
        db=db,
        message=payload.message,
        message_id=user_message.id,
        user_id=user_id,
    )
    autonomous_learning = maybe_autonomously_update_preferences(db=db, user_id=user_id)
    if autonomous_learning.updates:
        preference_learning.updates.extend(autonomous_learning.updates)
    preferences = preference_learning.profile
    model_history = _model_prompt_history(
        db=db,
        conversation=conversation,
        history=effective_history,
        latest_message=payload.message,
        user_id=user_id,
    )

    if route.action == "acknowledge":
        reply = route.reply or _preference_acknowledgement(preference_learning) or (
            "You are welcome. I am here when you want to keep going."
        )
        logger.info("\u2705 chat.message.complete action=acknowledge saved=False")
        response = ChatResponse(action="acknowledge", message=reply, saved=False)
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "conversation":
        if route.reply is not None:
            reply = route.reply
        elif _is_session_conversation(normalized_message=payload.message.lower()):
            reply = route.reply or _conversation_reply(
                message=payload.message,
                previous_user_turns=_conversation_user_messages(conversation),
            )
        else:
            high_confidence_context = (
                _search_for_conversation_context(
                    db=db,
                    message=payload.message,
                    embedder=embedder,
                    user_id=user_id,
                )
                if _should_probe_memory_for_conversation(
                    message=payload.message,
                    history=effective_history,
                )
                else _empty_search_response(query=payload.message)
            )
            high_confidence_context = _pack_memory_context(
                db=db,
                search=high_confidence_context,
                max_tokens=MEMORY_CONTEXT_TOKEN_BUDGET,
            )
            if high_confidence_context.results:
                relation_context = _relation_context_for_results(
                    db=db,
                    memory_ids=[result.memory_id for result in high_confidence_context.results],
                )
                synthesis = synthesizer.synthesize(
                    question=payload.message,
                    history=model_history,
                    search=high_confidence_context,
                    relation_context=relation_context,
                    preferences=preferences,
                )
                logger.info(
                    "\u2705 chat.message.complete action=answer source=strong_conversation_context evidence=%s",
                    len(high_confidence_context.results),
                )
                response = ChatResponse(
                    action="answer",
                    message=synthesis.answer,
                    saved=False,
                    evidence=high_confidence_context.results,
                    knowledge_gaps=synthesis.knowledge_gaps,
                    tensions=synthesis.tensions,
                    next_step=synthesis.next_step,
                )
                response = _with_preference_learning(response, preference_learning)
                return _persist_assistant_response(
                    db=db,
                    conversation=conversation,
                    user_message=user_message,
                    response=response,
                    user_id=user_id,
                )

            reply = route.reply or conversation_responder.respond(
                message=payload.message,
                history=model_history,
                preferences=preferences,
            )
        logger.info("\u2705 chat.message.complete action=conversation saved=False")
        response = ChatResponse(action="conversation", message=reply, saved=False)
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "self":
        response = _process_self_question(payload.message)
        response = _with_preference_learning(response, preference_learning)
        logger.info("\u2705 chat.message.complete action=self saved=False")
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "forget":
        response = _process_forget_request(
            db=db,
            conversation=conversation,
            message=payload.message,
            embedder=embedder,
            user_id=user_id,
        )
        logger.info(
            "\u2705 chat.message.complete action=forget candidates=%s",
            len(response.evidence),
        )
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "reminder":
        response = _process_reminder_request(
            db=db,
            message=payload.message,
            conversation_id=conversation.id,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=user_id,
        )
        logger.info(
            "\u2705 chat.message.complete action=reminder saved=%s",
            response.saved,
        )
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "capture":
        if url := _first_url(payload.message):
            if _should_capture_mixed_url_message_as_text(payload.message):
                capture = create_text_capture(
                    db=db,
                    payload=TextCaptureRequest(
                        content=payload.message,
                        intent_text=(
                            "The user pasted a learning note that includes a link. "
                            "Preserve the full note and treat the link as supporting context."
                        ),
                    ),
                    extractor=extractor,
                    embedder=embedder,
                    relation_detector=relation_detector,
                    user_id=user_id,
                )
            elif _is_reference_only_url(url):
                if not _has_explicit_url_capture_intent(payload.message):
                    response = ChatResponse(
                        action="conversation",
                        message=_url_capture_confirmation_prompt(url=url),
                        saved=False,
                        next_step="Reply with a short reason, or say \"save it\" to keep the link itself.",
                    )
                    response = _with_preference_learning(response, preference_learning)
                    logger.info("\u2705 chat.message.complete action=url_reference_confirmation saved=False")
                    return _persist_assistant_response(
                        db=db,
                        conversation=conversation,
                        user_message=user_message,
                        response=response,
                        user_id=user_id,
                    )
                capture = _create_reference_link_capture(
                    db=db,
                    url=url,
                    intent_text=_message_without_url(payload.message, url) or None,
                    embedder=embedder,
                    user_id=user_id,
                )
            elif reason := unsupported_url_reason(url):
                response = ChatResponse(
                    action="conversation",
                    message=reason,
                    saved=False,
                    next_step=(
                        "If the link matters, paste a short note about why and I can save that context instead."
                    ),
                )
                response = _with_preference_learning(response, preference_learning)
                logger.info("\u2705 chat.message.complete action=url_unsupported saved=False")
                return _persist_assistant_response(
                    db=db,
                    conversation=conversation,
                    user_message=user_message,
                    response=response,
                    user_id=user_id,
                )
            elif not _has_explicit_url_capture_intent(payload.message):
                response = ChatResponse(
                    action="conversation",
                    message=_url_capture_confirmation_prompt(url=url),
                    saved=False,
                    next_step="Reply with \"save this link\" if you want Crowscap to read and remember it.",
                )
                response = _with_preference_learning(response, preference_learning)
                logger.info("\u2705 chat.message.complete action=url_confirmation saved=False")
                return _persist_assistant_response(
                    db=db,
                    conversation=conversation,
                    user_message=user_message,
                    response=response,
                    user_id=user_id,
                )
            else:
                intent_text = _message_without_url(payload.message, url)
                try:
                    capture = create_url_capture(
                        db=db,
                        payload=UrlCaptureRequest(
                            url=url,
                            intent_text=intent_text or None,
                        ),
                        extractor=extractor,
                        embedder=embedder,
                        relation_detector=relation_detector,
                        user_id=user_id,
                    )
                except IngestionError as exc:
                    response = _url_ingestion_failure_response(url=url, error_message=str(exc))
                    response = _with_preference_learning(response, preference_learning)
                    logger.info("\u2705 chat.message.complete action=url_ingestion_failed saved=False")
                    return _persist_assistant_response(
                        db=db,
                        conversation=conversation,
                        user_message=user_message,
                        response=response,
                        user_id=user_id,
                    )
        elif _should_capture_pending_url(
            payload.message,
            pending_url=pending_url,
            route=route,
        ):
            if pending_url is None:
                if _is_save_previous_response_command(payload.message):
                    response = _process_save_previous_response_request(
                        db=db,
                        conversation=conversation,
                        extractor=extractor,
                        embedder=embedder,
                        relation_detector=relation_detector,
                        user_id=user_id,
                    )
                    response = _with_preference_learning(response, preference_learning)
                    logger.info(
                        "\u2705 chat.message.complete action=save_previous_response saved=%s",
                        response.saved,
                    )
                    return _persist_assistant_response(
                        db=db,
                        conversation=conversation,
                        user_message=user_message,
                        response=response,
                        user_id=user_id,
                    )
                response = ChatResponse(
                    action="conversation",
                    message=(
                        "I do not see a pending link in this chat. Send the link again with "
                        "\"save this\" and I will capture it."
                    ),
                    saved=False,
                )
                response = _with_preference_learning(response, preference_learning)
                logger.info("\u2705 chat.message.complete action=url_confirmation_missing saved=False")
                return _persist_assistant_response(
                    db=db,
                    conversation=conversation,
                    user_message=user_message,
                    response=response,
                    user_id=user_id,
                )
            if _is_reference_only_url(pending_url):
                capture = _create_reference_link_capture(
                    db=db,
                    url=pending_url,
                    intent_text=_pending_link_confirmation_intent(payload.message),
                    embedder=embedder,
                    user_id=user_id,
                )
            elif reason := unsupported_url_reason(pending_url):
                response = ChatResponse(
                    action="conversation",
                    message=reason,
                    saved=False,
                    next_step=(
                        "If the link matters, paste a short note about why and I can save that context instead."
                    ),
                )
                response = _with_preference_learning(response, preference_learning)
                logger.info("\u2705 chat.message.complete action=url_unsupported saved=False")
                return _persist_assistant_response(
                    db=db,
                    conversation=conversation,
                    user_message=user_message,
                    response=response,
                    user_id=user_id,
                )
            elif _should_save_pending_url_as_reference_after_failed_read(
                payload.message,
                history=effective_history,
            ):
                capture = _create_reference_link_capture(
                    db=db,
                    url=pending_url,
                    intent_text="Saved as a reference after Crowscap could not read the link content.",
                    embedder=embedder,
                    user_id=user_id,
                )
            else:
                try:
                    capture = create_url_capture(
                        db=db,
                        payload=UrlCaptureRequest(
                            url=pending_url,
                            intent_text="Confirmed from a previous link in chat.",
                        ),
                        extractor=extractor,
                        embedder=embedder,
                        relation_detector=relation_detector,
                        user_id=user_id,
                    )
                except IngestionError as exc:
                    response = _url_ingestion_failure_response(url=pending_url, error_message=str(exc))
                    response = _with_preference_learning(response, preference_learning)
                    logger.info("\u2705 chat.message.complete action=url_ingestion_failed saved=False")
                    return _persist_assistant_response(
                        db=db,
                        conversation=conversation,
                        user_message=user_message,
                        response=response,
                        user_id=user_id,
                    )
        elif _is_save_previous_response_command(payload.message):
            response = _process_save_previous_response_request(
                db=db,
                conversation=conversation,
                extractor=extractor,
                embedder=embedder,
                relation_detector=relation_detector,
                user_id=user_id,
            )
            response = _with_preference_learning(response, preference_learning)
            logger.info(
                "\u2705 chat.message.complete action=save_previous_response saved=%s",
                response.saved,
            )
            return _persist_assistant_response(
                db=db,
                conversation=conversation,
                user_message=user_message,
                response=response,
                user_id=user_id,
            )
        else:
            if not _is_substantial_direct_capture(payload.message):
                response = ChatResponse(
                    action="conversation",
                    message=(
                        "I need the actual content before I can save it. Paste the note, source, "
                        "or link you want kept, or say \"save that\" right after an answer from me."
                    ),
                    saved=False,
                    next_step="Send the thing to save, or refer to the previous answer with \"save that\".",
                )
                response = _with_preference_learning(response, preference_learning)
                logger.info("\u2705 chat.message.complete action=capture_too_short saved=False")
                return _persist_assistant_response(
                    db=db,
                    conversation=conversation,
                    user_message=user_message,
                    response=response,
                    user_id=user_id,
                )
            capture = create_text_capture(
                db=db,
                payload=TextCaptureRequest(content=payload.message),
                extractor=extractor,
                embedder=embedder,
                relation_detector=relation_detector,
                user_id=user_id,
            )
        logger.info(
            "\u2705 chat.message.complete action=capture saved=True memories=%s",
            len(capture.memories),
        )
        response = ChatResponse(
            action="capture",
            message=_capture_confirmation(capture),
            saved=True,
            capture=capture,
        )
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "audit":
        audit = belief_auditor.audit(
            db=db,
            payload=BeliefAuditRequest(topic=_audit_topic_from_message(payload.message)),
            user_id=user_id,
        )
        logger.info(
            "✅ chat.message.complete action=audit saved=False memories=%s public=%s",
            len(audit.memories),
            len(audit.public_evidence),
        )
        response = ChatResponse(
            action="audit",
            message=audit.answer,
            saved=False,
            evidence=audit.memories,
            knowledge_gaps=audit.unsupported_or_weak_points,
            tensions=audit.ideas_to_compare,
            next_step=audit.next_questions[0] if audit.next_questions else None,
            audit=audit,
        )
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    search = search_memories(
        db=db,
        payload=SearchRequest(
            query=_retrieval_query(message=payload.message, history=effective_history),
            limit=6,
            min_score=MEMORY_QUERY_MIN_SCORE,
            include_archived=False,
        ),
        embedder=embedder,
        user_id=user_id,
    )
    search = _pack_memory_context(
        db=db,
        search=search,
        max_tokens=MEMORY_CONTEXT_TOKEN_BUDGET,
    )
    relation_context = _relation_context_for_results(
        db=db,
        memory_ids=[result.memory_id for result in search.results],
    )
    synthesis = synthesizer.synthesize(
        question=payload.message,
        history=model_history,
        search=search,
        relation_context=relation_context,
        preferences=preferences,
    )
    logger.info(
        "\u2705 chat.message.complete action=answer saved=False evidence=%s gaps=%s tensions=%s",
        len(search.results),
        len(synthesis.knowledge_gaps),
        len(synthesis.tensions),
    )
    response = ChatResponse(
        action="answer",
        message=synthesis.answer,
        saved=False,
        evidence=search.results,
        knowledge_gaps=synthesis.knowledge_gaps,
        tensions=synthesis.tensions,
        next_step=synthesis.next_step,
    )
    response = _with_preference_learning(response, preference_learning)
    return _persist_assistant_response(
        db=db,
        conversation=conversation,
        user_message=user_message,
        response=response,
        user_id=user_id,
    )


def process_chat_pdf_upload(
    *,
    db: Session,
    file_bytes: bytes,
    filename: str,
    conversation_id: str | None,
    intent_text: str | None,
    user_note: str | None,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_id: str | None = None,
) -> ChatResponse:
    user_text = f"Uploaded PDF: {filename}"
    conversation = _get_or_create_conversation(
        db=db,
        conversation_id=conversation_id,
        first_message=user_text,
        user_id=user_id,
    )
    logger.info(
        "\U0001f4c4 chat.pdf.start filename=%s bytes=%s conversation_id=%s",
        filename,
        len(file_bytes),
        conversation.id,
    )

    user_message = ChatMessage(
        conversation_id=conversation.id,
        user_id=user_id,
        role="user",
        content=user_text,
    )
    db.add(user_message)
    db.flush()

    capture = create_pdf_capture_from_bytes(
        db=db,
        file_bytes=file_bytes,
        filename=filename,
        intent_text=intent_text,
        user_note=user_note,
        extractor=extractor,
        embedder=embedder,
        relation_detector=relation_detector,
        user_id=user_id,
    )
    logger.info(
        "\u2705 chat.pdf.complete memories=%s conversation_id=%s",
        len(capture.memories),
        conversation.id,
    )
    response = ChatResponse(
        action="capture",
        message=_capture_confirmation(capture),
        saved=True,
        capture=capture,
    )
    return _persist_assistant_response(
        db=db,
        conversation=conversation,
        user_message=user_message,
        response=response,
        user_id=user_id,
    )


def _get_or_create_conversation(
    *,
    db: Session,
    conversation_id: str | None,
    first_message: str,
    user_id: str | None,
) -> Conversation:
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None and user_id is not None and conversation.user_id != user_id:
            logger.warning(
                "🔒 chat.conversation.cross_user_rejected requested_id=%s owner=%s user_id=%s action=create_new",
                conversation_id,
                conversation.user_id,
                user_id,
            )
        elif conversation is not None:
            return conversation
        else:
            logger.info(
                "💬 chat.conversation.missing requested_id=%s action=create_new",
                conversation_id,
            )

    conversation = Conversation(
        user_id=user_id,
        title=_conversation_title(first_message),
        status="active",
    )
    db.add(conversation)
    db.flush()
    logger.info("\U0001f4ac chat.conversation.created conversation_id=%s", conversation.id)
    return conversation


def _conversation_title(message: str) -> str:
    compact = re.sub(r"\s+", " ", message.strip())
    if not compact:
        return "New thought"
    return compact[:70].rstrip(" .,;:") or "New thought"


def _conversation_turns(conversation: Conversation, *, limit: int | None = 12) -> list[ConversationTurn]:
    turns = [
        ConversationTurn(role=message.role, content=message.content.strip()[:4000])
        for message in conversation.messages
        if message.role in {"user", "assistant"}
        and message.content.strip()
        and _message_belongs_to_conversation_owner(conversation, message)
    ]
    return turns if limit is None else turns[-limit:]


def _conversation_user_messages(conversation: Conversation) -> list[str]:
    return [
        message.content.strip()
        for message in conversation.messages
        if message.role == "user"
        and message.content.strip()
        and _message_belongs_to_conversation_owner(conversation, message)
    ]


def _model_prompt_history(
    *,
    db: Session,
    conversation: Conversation,
    history: list[ConversationTurn],
    latest_message: str,
    user_id: str | None,
) -> list[ConversationTurn]:
    prompt_history = _compress_conversation_history(history)
    if not _should_include_recent_capture_context(message=latest_message, history=history):
        return prompt_history

    recent_capture = _latest_captured_source_from_conversation(
        db=db,
        conversation=conversation,
        user_id=user_id,
        source_type_hint=None,
    )
    if recent_capture is None:
        return prompt_history

    capture_turn = _recent_capture_context_turn(recent_capture)
    if capture_turn is None:
        return prompt_history
    return [capture_turn, *prompt_history]


def _compress_conversation_history(history: list[ConversationTurn]) -> list[ConversationTurn]:
    if len(history) <= PROMPT_HISTORY_SUMMARY_TRIGGER_TURNS:
        return history

    older_turns = history[:-PROMPT_HISTORY_RECENT_TURNS]
    recent_turns = history[-PROMPT_HISTORY_RECENT_TURNS:]
    summary = _summarize_turns_for_context(older_turns)
    if summary is None:
        return recent_turns
    return [ConversationTurn(role="assistant", content=summary), *recent_turns]


def _summarize_turns_for_context(turns: list[ConversationTurn]) -> str | None:
    user_topics: list[str] = []
    app_events: list[str] = []
    for turn in turns:
        content = re.sub(r"\s+", " ", turn.content.strip())
        if not content:
            continue
        if turn.role == "user":
            normalized = content.lower()
            if len(content) < 4 or _is_greeting_word(normalized):
                continue
            if _looks_like_acknowledgement_only(normalized):
                continue
            user_topics.append(_snippet(content, max_chars=180))
        elif (
            "I kept this as" in content
            or "I found this link" in content
            or "reminder scheduled" in content.lower()
            or "archived" in content.lower()
            or "updated your Crowscap preferences" in content
        ):
            app_events.append(_snippet(content, max_chars=180))

    parts: list[str] = [
        "Conversation summary for older turns. Exact older messages are omitted to keep model context small."
    ]
    if user_topics:
        parts.append("User topics: " + "; ".join(user_topics[-5:]) + ".")
    if app_events:
        parts.append("Crowscap events: " + "; ".join(app_events[-4:]) + ".")
    if len(parts) == 1:
        return None
    return " ".join(parts)[:3800]


def _recent_capture_context_turn(recent: RecentCaptureContext) -> ConversationTurn | None:
    active_memories = [
        memory
        for memory in recent.memories
        if memory.status == "active" and memory.content.strip()
    ]
    if not active_memories:
        return None

    source_label = recent.source.title or recent.source.original_url or recent.source.resolved_url or recent.source.source_type
    memory_lines = [
        f"- {memory.memory_type}: {_snippet(memory.content, max_chars=280)}"
        for memory in active_memories[:6]
    ]
    content = (
        "Immediate context from the source the user just saved. Use this only for short follow-ups "
        f"about the just-saved source, not as general long-term memory. Source: {source_label}. "
        "Extracted memories:\n"
        + "\n".join(memory_lines)
    )
    return ConversationTurn(role="assistant", content=content[:4000])


def _should_include_recent_capture_context(
    *,
    message: str,
    history: list[ConversationTurn],
) -> bool:
    if not _has_recent_capture_receipt(history):
        return False

    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if (
        _is_explicit_memory_query(normalized)
        or _is_explicit_belief_audit_query(normalized)
        or _is_forget_command(normalized)
        or _is_reminder_command(normalized)
    ):
        return False

    words = re.findall(r"[a-z0-9']+", normalized)
    if not words:
        return False

    local_reference_words = {
        "this",
        "that",
        "it",
        "these",
        "those",
        "there",
        "deep",
        "interesting",
        "serious",
        "true",
        "right",
        "wrong",
        "mean",
        "means",
        "meaning",
    }
    if len(words) <= 12 and (
        _is_short_conversation_followup(normalized)
        or any(word in local_reference_words for word in words)
    ):
        return True
    return False


def _has_recent_capture_receipt(history: list[ConversationTurn]) -> bool:
    receipt_markers = (
        "I kept this as",
        "I kept this link as",
        "Memory receipt",
        "distinct memories",
    )
    for turn in reversed(history[-8:]):
        if turn.role == "assistant" and any(marker in turn.content for marker in receipt_markers):
            return True
    return False


def _snippet(text: str, *, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip(" .,;:") + "..."


def _looks_like_acknowledgement_only(normalized: str) -> bool:
    words = re.findall(r"[a-z0-9']+", normalized)
    if not words or len(words) > 12:
        return False
    acknowledgement_words = {
        "ok",
        "okay",
        "alright",
        "cool",
        "great",
        "thanks",
        "thank",
        "you",
        "got",
        "it",
        "understood",
        "sense",
        "makes",
        "this",
        "that",
        "so",
        "much",
        "really",
        "appreciate",
        "appreciated",
        "exactly",
        "clear",
        "understand",
        "i",
        "helpful",
        "perfect",
        "nice",
        "yes",
        "yeah",
        "yep",
        "hmm",
        "hmmm",
    }
    return set(words).issubset(acknowledgement_words)


def _conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=[
            ChatMessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                action=message.action,
                metadata_json=message.metadata_json,
                created_at=message.created_at.isoformat(),
            )
            for message in conversation.messages
            if message.role in {"user", "assistant"}
            and _message_belongs_to_conversation_owner(conversation, message)
        ],
    )


def _message_belongs_to_conversation_owner(
    conversation: Conversation,
    message: ChatMessage,
) -> bool:
    return conversation.user_id is None or message.user_id == conversation.user_id


def _persist_assistant_response(
    *,
    db: Session,
    conversation: Conversation,
    user_message: ChatMessage,
    response: ChatResponse,
    user_id: str | None,
) -> ChatResponse:
    response.conversation_id = conversation.id
    response.user_message_id = user_message.id

    if conversation.user_id is None and user_id is not None:
        conversation.user_id = user_id

    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        user_id=user_id,
        role="assistant",
        content=response.message,
        action=response.action,
    )
    db.add(assistant_message)
    db.flush()

    response.assistant_message_id = assistant_message.id
    assistant_message.metadata_json = response.model_dump(mode="json")
    conversation.updated_at = utc_now()

    db.commit()
    logger.info(
        "\U0001f4be chat.message.persisted conversation_id=%s user_message_id=%s assistant_message_id=%s action=%s",
        conversation.id,
        user_message.id,
        assistant_message.id,
        response.action,
    )
    return response


def _with_preference_learning(
    response: ChatResponse,
    learning: PreferenceLearningResult,
) -> ChatResponse:
    if learning.updates:
        response.preference_updates = learning.updates
        response.preferences = preference_response(learning.profile)
    return response


def _preference_acknowledgement(learning: PreferenceLearningResult) -> str | None:
    if not learning.updates:
        return None
    updates = "; ".join(learning.updates)
    return f"Got it. I updated your Crowscap preferences: {updates}."


def _search_for_conversation_context(
    *,
    db: Session,
    message: str,
    embedder: MemoryEmbedder,
    user_id: str | None,
) -> SearchResponse:
    search = search_memories(
        db=db,
        payload=SearchRequest(
            query=message,
            limit=3,
            min_score=CONVERSATION_MEMORY_MIN_SCORE,
            include_archived=False,
        ),
        embedder=embedder,
        user_id=user_id,
    )
    logger.info(
        "\U0001f9ed chat.conversation.memory_probe returned=%s threshold=%s top_score=%s",
        len(search.results),
        CONVERSATION_MEMORY_MIN_SCORE,
        search.top_score,
    )
    return search


def _empty_search_response(*, query: str) -> SearchResponse:
    return SearchResponse(
        query=query,
        min_score=CONVERSATION_MEMORY_MIN_SCORE,
        candidate_count=0,
        embedded_candidate_count=0,
        returned_count=0,
        top_score=None,
        results=[],
    )


def _pack_memory_context(
    *,
    db: Session,
    search: SearchResponse,
    max_tokens: int,
) -> SearchResponse:
    if not search.results:
        return search

    memories_by_id = {
        memory.id: memory
        for memory in db.scalars(
            select(Memory).where(Memory.id.in_([result.memory_id for result in search.results]))
        ).all()
    }
    ranked = sorted(
        search.results,
        key=lambda result: _memory_context_priority(
            result=result,
            memory=memories_by_id.get(result.memory_id),
        ),
        reverse=True,
    )

    kept: list[SearchResult] = []
    token_count = 0
    dropped_duplicates = 0
    dropped_budget = 0
    for result in ranked:
        if any(_memory_texts_are_near_duplicate(result.content, kept_result.content) for kept_result in kept):
            dropped_duplicates += 1
            continue

        estimate = _memory_context_token_estimate(result)
        if kept and token_count + estimate > max_tokens:
            dropped_budget += 1
            continue

        kept.append(result)
        token_count += estimate

    logger.info(
        "\U0001f9ee chat.context_pack before=%s after=%s estimated_tokens=%s dropped_duplicates=%s dropped_budget=%s",
        len(search.results),
        len(kept),
        token_count,
        dropped_duplicates,
        dropped_budget,
    )
    return search.model_copy(
        update={
            "results": kept,
            "returned_count": len(kept),
            "top_score": kept[0].similarity_score if kept else search.top_score,
        }
    )


def _memory_context_priority(*, result: SearchResult, memory: Memory | None) -> float:
    similarity = max(0.0, min(float(result.similarity_score), 1.0))
    confidence = _confidence_weight(str(result.confidence))
    source_strength = _source_strength_weight(str(result.source_strength))
    recency = _recency_weight(memory.created_at if memory is not None else None)
    return (0.4 * similarity) + (0.3 * confidence) + (0.2 * source_strength) + (0.1 * recency)


def _confidence_weight(value: str) -> float:
    return {
        "high": 1.0,
        "medium": 0.66,
        "low": 0.33,
        "unknown": 0.4,
    }.get(value, 0.4)


def _source_strength_weight(value: str) -> float:
    return {
        "strong": 1.0,
        "moderate": 0.66,
        "weak": 0.33,
        "unknown": 0.4,
    }.get(value, 0.4)


def _recency_weight(created_at: datetime | None) -> float:
    if created_at is None:
        return 0.5
    now = utc_now()
    if created_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    age = now - created_at
    age_days = max(age.total_seconds() / 86_400, 0.0)
    return max(0.0, min(1.0, 1.0 - (age_days / 180.0)))


def _memory_context_token_estimate(result: SearchResult) -> int:
    packed = " ".join(
        part
        for part in (
            result.content,
            result.source_title or "",
            str(result.memory_type),
            str(result.epistemic_label or ""),
            str(result.confidence),
            str(result.source_strength),
        )
        if part
    )
    return max(1, len(packed) // 4)


def _memory_texts_are_near_duplicate(left: str, right: str) -> bool:
    left_norm = _normalize_memory_text(left)
    right_norm = _normalize_memory_text(right)
    if not left_norm or not right_norm:
        return False
    return SequenceMatcher(None, left_norm, right_norm).ratio() >= MEMORY_NEAR_DUPLICATE_RATIO


def _normalize_memory_text(text: str) -> str:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return " ".join(words)


def _is_session_conversation(*, normalized_message: str) -> bool:
    normalized = re.sub(r"\s+", " ", normalized_message.strip())
    return any(marker in normalized for marker in SESSION_CONVERSATION_MARKERS)


def _conversation_reply(*, message: str, previous_user_turns: list[str]) -> str:
    normalized = re.sub(r"\s+", " ", message.strip().lower())

    if _is_first_message_question(normalized):
        if not previous_user_turns:
            return "I cannot find an earlier user message in this conversation."
        return f'Your first message in this chat was: "{previous_user_turns[0]}"'

    if "thank" in normalized and (
        "before" in normalized
        or "b4" in normalized
        or "earlier" in normalized
        or "this chat" in normalized
        or "this conversation" in normalized
    ):
        thanked_turns = [
            content
            for content in previous_user_turns
            if re.search(r"\b(thanks|thank you|appreciate|grateful)\b", content.lower())
        ]
        if not thanked_turns:
            return "Not in this chat so far. This is the first time you have asked about it here."
        count_text = "once" if len(thanked_turns) == 1 else f"{len(thanked_turns)} times"
        return f"Yes, you thanked me {count_text} earlier in this chat."

    if "last message" in normalized or "just say" in normalized or "just said" in normalized:
        if not previous_user_turns:
            return "There is no earlier user message in this chat yet."
        return f'Your last message was: "{previous_user_turns[-1]}"'

    return "I am with you. This part is just normal conversation, so I am not saving it as a memory."


def _grounded_local_conversation_reply(
    *,
    db: Session,
    message: str,
    history: list[ConversationTurn],
    conversation: Conversation,
    user_id: str | None,
) -> str | None:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    previous_user_turns = _conversation_user_messages(conversation)

    if _asks_about_recent_archive(normalized):
        return _recent_archive_summary_reply(db=db, conversation=conversation, user_id=user_id)

    if _is_first_message_question(normalized):
        return _conversation_reply(message=message, previous_user_turns=previous_user_turns)

    if (
        "thank" in normalized
        and any(marker in normalized for marker in ("before", "b4", "earlier", "this chat", "this conversation"))
    ):
        return _conversation_reply(message=message, previous_user_turns=previous_user_turns)

    if normalized in {"what question", "which question", "what question was that", "which one"}:
        question = _last_substantive_user_question(history)
        if question is None:
            return "I meant the question we were discussing, but I cannot find the exact earlier question in this chat."
        return f'I meant your earlier question: "{question}"'

    if _asks_why_assistant_used_previous_phrase(normalized):
        subject = _last_substantive_user_question(history) or _last_substantive_user_statement(history)
        if subject is None:
            return "I was reacting to the idea we were discussing, but I cannot find the exact earlier line now."
        return f'I was reacting to this: "{subject}"'

    return None


def _asks_about_recent_archive(normalized: str) -> bool:
    if _is_forget_command(normalized):
        return False
    if not any(word in normalized for word in ("archive", "archived", "delete", "deleted", "remove", "removed")):
        return False
    if not any(marker in normalized for marker in ("what", "which", "show", "list", "tell me")):
        return False
    return any(marker in normalized for marker in ("just", "last", "recent", "that", "those"))


def _recent_archive_summary_reply(
    *,
    db: Session,
    conversation: Conversation,
    user_id: str | None,
) -> str:
    query = (
        select(MemoryArchiveEvent)
        .where(MemoryArchiveEvent.created_at >= conversation.created_at)
        .order_by(MemoryArchiveEvent.created_at.desc(), MemoryArchiveEvent.id.desc())
        .limit(60)
    )
    query = query.where(MemoryArchiveEvent.user_id.is_(None) if user_id is None else MemoryArchiveEvent.user_id == user_id)
    events = list(db.scalars(query))
    scoped_events = [
        event
        for event in events
        if isinstance(event.metadata_json, dict) and event.metadata_json.get("conversation_id") == conversation.id
    ]
    if scoped_events:
        events = scoped_events
    if not events:
        return "I do not see a recent archive action in this chat."

    latest = events[0]
    latest_meta = latest.metadata_json or {}
    capture_id = latest_meta.get("capture_id")
    source_id = latest_meta.get("source_id")
    if capture_id:
        grouped_events = [
            event
            for event in events
            if isinstance(event.metadata_json, dict) and event.metadata_json.get("capture_id") == capture_id
        ]
    else:
        grouped_events = [latest]

    memories: list[Memory] = []
    for event in reversed(grouped_events):
        memory = db.get(Memory, event.memory_id)
        if memory is not None:
            memories.append(memory)

    if not memories:
        return "I archived something recently, but I cannot recover the exact memory text from the database."

    source = db.get(Source, source_id) if isinstance(source_id, str) else None
    source_text = f" from {_source_display_name(source)}" if source is not None else ""
    lines = [f"I just archived these {len(memories)} memories{source_text}:"]
    for memory in memories[:8]:
        lines.append(f"- {memory.content}")
    if len(memories) > 8:
        lines.append(f"- ...and {len(memories) - 8} more.")
    return "\n".join(lines)


def _asks_why_assistant_used_previous_phrase(normalized: str) -> bool:
    patterns = (
        r"^what\s+(?:made|make|makes)\s+you\s+say\s+.+$",
        r"^why\s+did\s+you\s+say\s+.+$",
        r"^why\s+say\s+.+$",
        r"^what\s+is\s+deep(?:\s+indeed)?$",
        r"^what'?s\s+deep(?:\s+indeed)?$",
    )
    return any(re.fullmatch(pattern, normalized) is not None for pattern in patterns)


def _last_substantive_user_question(history: list[ConversationTurn]) -> str | None:
    for turn in reversed(history):
        if turn.role != "user":
            continue
        content = re.sub(r"\s+", " ", turn.content.strip())
        normalized = content.lower().strip(" .!?")
        if not content or _is_greeting_word(normalized):
            continue
        if _looks_like_acknowledgement_only(normalized):
            continue
        if _is_local_meta_followup(normalized):
            continue
        words = re.findall(r"[a-z0-9']+", normalized)
        if "?" in content or normalized.startswith(("what ", "why ", "how ", "can ", "should ", "do ")):
            if len(words) >= 4 or _is_explicit_memory_query(normalized) or _is_explicit_belief_audit_query(normalized):
                return content
    return None


def _last_substantive_user_statement(history: list[ConversationTurn]) -> str | None:
    for turn in reversed(history):
        if turn.role != "user":
            continue
        content = re.sub(r"\s+", " ", turn.content.strip())
        normalized = content.lower().strip(" .!?")
        if not content or _is_greeting_word(normalized):
            continue
        if _looks_like_acknowledgement_only(normalized) or _is_local_meta_followup(normalized):
            continue
        if _first_url(content):
            continue
        if len(re.findall(r"[a-z0-9']+", normalized)) >= 4:
            return content
    return None


def _is_local_meta_followup(normalized: str) -> bool:
    meta_markers = (
        "what question",
        "which question",
        "what make you say",
        "what made you say",
        "what makes you say",
        "why did you say",
        "why say",
        "what is deep",
        "what's deep",
        "what do you mean",
    )
    return any(marker in normalized for marker in meta_markers)


def _is_first_message_question(normalized: str) -> bool:
    first_markers = (
        "first thing i said",
        "very first thing",
        "first message",
        "first thing",
        "beginning of our chat",
        "beginning of this chat",
        "start of our chat",
        "start of this chat",
    )
    return any(marker in normalized for marker in first_markers)


def _process_self_question(message: str) -> ChatResponse:
    normalized = re.sub(r"\s+", " ", message.strip().lower())

    if _is_save_capability_question(normalized):
        answer = (
            "I can help you keep the things you do not want to lose.\n\n"
            "- Ideas you are still thinking through\n"
            "- Links, notes, PDFs, and videos you want to revisit\n"
            "- Reminders tied to something important\n"
            "- Lessons from your work, reading, or research\n"
            "- Beliefs or decisions you may want to question later\n\n"
            "The point is simple: when something matters, I help it come back at the right time."
        )
        next_step = "Send me anything worth keeping."
    elif any(marker in normalized for marker in ("what can", "can you do", "features", "capabilities")):
        answer = (
            "Crowscap helps your learning survive past the moment you found it.\n\n"
            "- Save ideas, sources, reminders, and decisions\n"
            "- Ask what you know about a topic\n"
            "- Revisit important thoughts when they become useful again\n"
            "- Compare ideas you saved at different times\n"
            "- Check whether a belief needs stronger evidence\n\n"
            "It is built for people who collect important ideas but need help turning them into judgment."
        )
        next_step = "Save something, search your memory, or ask me to audit an idea."
    elif any(marker in normalized for marker in ("limit", "can't", "cannot", "not do", "what can't")):
        answer = (
            "Crowscap helps you reason with your saved knowledge; it does not replace your judgment. "
            "Public evidence in audits is treated as source leads, not final truth, and sensitive decisions "
            "still need context from the user.\n\n"
            "Current limits: reminders surface inside the app, native push notifications are not complete, "
            "passive capture from other apps is not built, and social-platform integrations are still future work."
        )
        next_step = "Tell me what you want to save, search, revisit, or question."
    else:
        answer = (
            "Crowscap is your private memory intelligence for learning.\n\n"
            "It helps you keep important ideas, sources, reminders, and decisions, then brings them back "
            "when they can help you think or act."
        )
        next_step = "Send me something worth keeping, or ask what you already know."

    return ChatResponse(
        action="self",
        message=answer,
        saved=False,
        next_step=next_step,
    )


def _retrieve_self_knowledge(message: str, *, limit: int = 3) -> list[SelfKnowledgeChunk]:
    query_tokens = set(re.findall(r"[a-z0-9']+", message.lower()))
    scored: list[tuple[int, SelfKnowledgeChunk]] = []
    for chunk in CROWSCAP_SELF_KNOWLEDGE:
        score = len(query_tokens.intersection(chunk.keywords))
        if score:
            scored.append((score, chunk))
    if not scored:
        return [
            CROWSCAP_SELF_KNOWLEDGE[0],
            CROWSCAP_SELF_KNOWLEDGE[1],
            CROWSCAP_SELF_KNOWLEDGE[4],
        ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:limit]]


def _process_forget_request(
    *,
    db: Session,
    conversation: Conversation,
    message: str,
    embedder: MemoryEmbedder,
    user_id: str | None,
) -> ChatResponse:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    memory_id = _explicit_memory_id(normalized)
    if memory_id is not None:
        try:
            archived = archive_memory(
                db=db,
                memory_id=memory_id,
                payload=ArchiveMemoryRequest(
                    reason="user_dismissed",
                    note="Archived from chat command.",
                ),
                user_id=user_id,
            )
        except LookupError:
            return ChatResponse(
                action="forget",
                message="I could not find that memory. It may already be archived or the id may be wrong.",
                saved=False,
            )
        return ChatResponse(
            action="forget",
            message=(
                "Done. I archived that memory, so it will stop appearing in active search, "
                "recall, audits, and nearby context."
            ),
            saved=False,
            next_step=f"Archived memory {archived.memory_id}.",
        )

    if recent_capture_response := _archive_recent_capture_if_referenced(
        db=db,
        conversation=conversation,
        message=message,
        user_id=user_id,
    ):
        return recent_capture_response

    topic = _forget_topic_from_message(message)
    if topic is None:
        return ChatResponse(
            action="forget",
            message=(
                "Yes. I can remove the last thing I saved in this chat, or archive memories by topic "
                "so they stop appearing in search, recall, audits, and nearby context."
            ),
            saved=False,
            next_step='Say "delete that" right after a save, or name what you want removed.',
        )

    search = search_memories(
        db=db,
        payload=SearchRequest(
            query=topic,
            limit=8,
            min_score=0.25,
            include_archived=False,
        ),
        embedder=embedder,
        user_id=user_id,
    )
    if not search.results:
        return ChatResponse(
            action="forget",
            message=f"I could not find active memories clearly connected to {topic!r}.",
            saved=False,
        )

    return ChatResponse(
        action="forget",
        message=(
            f"I found {len(search.results)} active memories connected to {topic!r}. "
            "I have not archived them yet because topic-level forgetting should be confirmed. "
            "You can archive a specific memory by id, or tell me to archive the weaker ones."
        ),
        saved=False,
        evidence=search.results,
        next_step="Choose specific memories to archive, or ask me to archive the weaker matches.",
    )


def _archive_recent_capture_if_referenced(
    *,
    db: Session,
    conversation: Conversation,
    message: str,
    user_id: str | None,
) -> ChatResponse | None:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if not _references_recent_capture(normalized, conversation=conversation):
        return None

    source_type_hint = _recent_capture_source_type_hint(normalized)
    recent = _latest_captured_source_from_conversation(
        db=db,
        conversation=conversation,
        user_id=user_id,
        source_type_hint=source_type_hint,
    )
    if recent is None:
        return ChatResponse(
            action="forget",
            message=(
                "I could not find a recent saved source in this chat to remove. "
                "If you want to remove older memories, name the topic or give me the memory id."
            ),
            saved=False,
        )

    archived_count = _archive_capture_memories(
        db=db,
        recent=recent,
        user_id=user_id,
        conversation_id=conversation.id,
    )
    source_label = _source_display_name(recent.source)
    plural = "memory" if archived_count == 1 else "memories"
    return ChatResponse(
        action="forget",
        message=(
            f"Done. I archived {archived_count} {plural} from {source_label}. "
            "They will no longer appear in active search, recall, audits, or nearby context."
        ),
        saved=False,
        next_step="If this was accidental, you can re-upload or re-save the source.",
    )


def _latest_captured_source_from_conversation(
    *,
    db: Session,
    conversation: Conversation,
    user_id: str | None,
    source_type_hint: str | None,
) -> RecentCaptureContext | None:
    query = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(40)
    )
    if conversation.user_id is not None:
        query = query.where(ChatMessage.user_id == conversation.user_id)
    elif user_id is not None:
        query = query.where(ChatMessage.user_id == user_id)
    else:
        query = query.where(ChatMessage.user_id.is_(None))

    for message in db.scalars(query):
        metadata = message.metadata_json or {}
        capture_payload = metadata.get("capture")
        if not isinstance(capture_payload, dict):
            continue
        capture_id = capture_payload.get("capture_id")
        if not isinstance(capture_id, str):
            continue
        capture = db.get(Capture, capture_id)
        if capture is None or (user_id is not None and capture.user_id != user_id):
            continue
        source = db.get(Source, capture.source_id)
        if source is None or (user_id is not None and source.user_id != user_id):
            continue
        if source_type_hint is not None and source.source_type != source_type_hint:
            continue
        memories_query = select(Memory).where(
            Memory.capture_id == capture.id,
            Memory.status == "active",
        )
        if user_id is not None:
            memories_query = memories_query.where(Memory.user_id == user_id)
        memories = list(db.scalars(memories_query))
        if memories:
            return RecentCaptureContext(capture=capture, source=source, memories=memories)
    return None


def _archive_capture_memories(
    *,
    db: Session,
    recent: RecentCaptureContext,
    user_id: str | None,
    conversation_id: str,
) -> int:
    archived_count = 0
    for memory in recent.memories:
        if user_id is not None and memory.user_id != user_id:
            continue
        previous_status = memory.status
        memory.status = "archived"
        memory.next_review_at = None
        db.add(
            MemoryArchiveEvent(
                user_id=memory.user_id,
                memory_id=memory.id,
                previous_status=previous_status,
                new_status="archived",
                reason="user_dismissed",
                note="Archived from contextual chat command for the most recent saved source.",
                created_by="user",
                metadata_json={
                    "capture_id": recent.capture.id,
                    "conversation_id": conversation_id,
                    "source_id": recent.source.id,
                    "source_type": recent.source.source_type,
                    "archive_scope": "recent_capture",
                },
            )
        )
        archived_count += 1
    db.commit()
    return archived_count


def _references_recent_capture(normalized: str, *, conversation: Conversation) -> bool:
    direct_markers = (
        "what you just saved",
        "what u just saved",
        "you just saved",
        "the last thing you saved",
        "last thing you saved",
        "what i just uploaded",
        "what i uploaded",
        "the pdf",
        "this pdf",
        "that pdf",
        "uploaded pdf",
        "the document",
        "that document",
        "the source",
        "that source",
        "the capture",
        "that capture",
    )
    if any(marker in normalized for marker in direct_markers):
        return True
    if _is_short_recent_capture_forget_command(normalized):
        return True
    if normalized in {"i mean the pdf", "i mean pdf", "pdf", "the pdf"}:
        return _previous_user_turn_was_forget(conversation)
    return False


def _is_short_recent_capture_forget_command(normalized: str) -> bool:
    words = re.findall(r"[a-z0-9']+", normalized)
    if not words or len(words) > 12:
        return False
    forget_verbs = {"archive", "delete", "forget", "remove", "clear", "erase"}
    pointer_words = {"that", "this", "it"}
    if not any(word in forget_verbs for word in words):
        return False
    if any(word in pointer_words for word in words):
        return True
    compact = " ".join(words)
    return any(
        marker in compact
        for marker in (
            "last saved",
            "latest saved",
            "recent saved",
            "last thing",
            "latest thing",
            "recent thing",
        )
    )


def _previous_user_turn_was_forget(conversation: Conversation) -> bool:
    user_turns = [
        message.content
        for message in conversation.messages
        if message.role == "user" and message.content.strip()
    ]
    for content in reversed(user_turns[:-1]):
        if _is_forget_command(re.sub(r"\s+", " ", content.strip().lower())):
            return True
        if _is_greeting_word(content.strip().lower()):
            continue
        break
    return False


def _recent_capture_source_type_hint(normalized: str) -> str | None:
    if any(marker in normalized for marker in ("pdf", "document", "file", "uploaded")):
        return "pdf"
    if "youtube" in normalized or "video" in normalized or "shorts" in normalized:
        return "youtube"
    if "article" in normalized or "link" in normalized or "url" in normalized:
        return "article"
    return None


def _is_save_capability_question(normalized: str) -> bool:
    save_markers = (
        "what can you save",
        "what can u save",
        "what do you save",
        "what do u save",
        "what can i save",
        "what should i save",
        "what can you keep",
        "what can u keep",
        "what can you remember",
        "what can u remember",
    )
    return any(marker in normalized for marker in save_markers)


def _source_display_name(source: Source) -> str:
    label = source.title or source.original_url or source.resolved_url or source.source_type
    if source.source_type == "pdf":
        return f"the PDF {label!r}"
    if source.source_type == "youtube":
        return f"the YouTube source {label!r}"
    if source.source_type == "article":
        return f"the article {label!r}"
    return f"the source {label!r}"


def _process_save_previous_response_request(
    *,
    db: Session,
    conversation: Conversation,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_id: str | None,
) -> ChatResponse:
    previous = _latest_assistant_response_for_saving(
        db=db,
        conversation=conversation,
        user_id=user_id,
    )
    if previous is None:
        return ChatResponse(
            action="capture",
            message=(
                "I do not have a previous answer in this chat to save yet. "
                "Send the note or source you want me to remember."
            ),
            saved=False,
        )

    content = previous.content.strip()
    if len(content) < 20:
        return ChatResponse(
            action="capture",
            message=(
                "The previous reply is too short to turn into a useful memory. "
                "Tell me the idea you want saved and I will capture it cleanly."
            ),
            saved=False,
        )

    capture = create_text_capture(
        db=db,
        payload=TextCaptureRequest(
            content=content,
            intent_text="The user asked Crowscap to save the previous assistant answer.",
            user_note="Saved from a contextual chat command such as 'save that'.",
            source_title=f"Crowscap conversation - {utc_now().date().isoformat()}",
        ),
        extractor=extractor,
        embedder=embedder,
        relation_detector=relation_detector,
        user_id=user_id,
    )
    return ChatResponse(
        action="capture",
        message=_capture_confirmation(capture),
        saved=True,
        capture=capture,
    )


def _latest_assistant_response_for_saving(
    *,
    db: Session,
    conversation: Conversation,
    user_id: str | None,
) -> ChatMessage | None:
    query = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(20)
    )
    if conversation.user_id is not None:
        query = query.where(ChatMessage.user_id == conversation.user_id)
    elif user_id is not None:
        query = query.where(ChatMessage.user_id == user_id)
    else:
        query = query.where(ChatMessage.user_id.is_(None))

    for message in db.scalars(query):
        metadata = message.metadata_json or {}
        if metadata.get("action") == "capture" and metadata.get("saved") is True:
            continue
        if "I have not saved it yet" in message.content:
            continue
        if message.content.strip():
            return message
    return None


def _process_reminder_request(
    *,
    db: Session,
    message: str,
    conversation_id: str,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_id: str | None,
) -> ChatResponse:
    reminder_intent = _parse_reminder_intent(message)
    if reminder_intent is None:
        return ChatResponse(
            action="reminder",
            message=(
                "I can do that, but I need both the reminder content and the time. "
                'For example: "remind me in 1 hour" followed by the note.'
            ),
            saved=False,
        )

    if reminder_intent.save_as_memory and len(reminder_intent.content) >= 20:
        capture = create_text_capture(
            db=db,
            payload=TextCaptureRequest(
                content=reminder_intent.content,
                intent_text=f"Remind me at {reminder_intent.due_at.isoformat()}",
                user_note="Scheduled from chat reminder command.",
            ),
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=user_id,
        )
        memory_ids = [memory.id for memory in capture.memories]
        memories = list(db.scalars(select(Memory).where(Memory.id.in_(memory_ids))).all())
        for memory in memories:
            memory.next_review_at = reminder_intent.due_at
        db.commit()
        reminder = create_reminder(
            db=db,
            content=reminder_intent.content,
            due_at=reminder_intent.due_at,
            conversation_id=conversation_id,
            memory_id=memory_ids[0] if memory_ids else None,
            save_as_memory=True,
            user_id=user_id,
            metadata_json={"memory_ids": memory_ids},
        )
        return ChatResponse(
            action="reminder",
            message=(
                f"Done. I saved this as {len(capture.memories)} memories and scheduled it "
                "to show under Recall when it is due."
            ),
            saved=True,
            capture=capture,
            reminder=reminder,
        )

    reminder = create_reminder(
        db=db,
        content=reminder_intent.content,
        due_at=reminder_intent.due_at,
        conversation_id=conversation_id,
        save_as_memory=False,
        user_id=user_id,
        metadata_json={"reason": "user_requested_no_memory"},
    )
    return ChatResponse(
        action="reminder",
        message=(
            "Done. I scheduled the reminder and did not save it as semantic memory. "
            "It will show under Recall when it is due."
        ),
        saved=False,
        reminder=reminder,
    )


def _explicit_memory_id(normalized_message: str) -> str | None:
    match = re.search(
        r"\b(?:memory|memory_id|id)\s*[:#-]?\s*"
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b",
        normalized_message,
    )
    return match.group(1) if match else None


def _forget_topic_from_message(message: str) -> str | None:
    compact = re.sub(r"\s+", " ", message.strip())
    normalized = compact.lower()
    if normalized in {
        "can you forget a memory?",
        "can you forget a memory",
        "can you forget memories?",
        "can you forget memories",
    }:
        return None

    patterns = [
        r"^forget\s+what\s+i\s+know\s+about\s+(.+)$",
        r"^forget\s+what\s+know\s+about\s+(.+)$",
        r"^forget\s+my\s+memories\s+about\s+(.+)$",
        r"^forget\s+memories\s+about\s+(.+)$",
        r"^archive\s+memories\s+about\s+(.+)$",
        r"^stop\s+reminding\s+me\s+about\s+(.+)$",
        r"^do\s+not\s+show\s+me\s+(.+?)\s+again$",
        r"^don't\s+show\s+me\s+(.+?)\s+again$",
        r"^dont\s+show\s+me\s+(.+?)\s+again$",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return match.group(1).strip(" ?.,;:") or None
    return None


def _parse_reminder_intent(message: str) -> ReminderIntent | None:
    due_at, time_phrase = _parse_due_time(message)
    if due_at is None or time_phrase is None:
        return None

    content = _reminder_content(message=message, time_phrase=time_phrase)
    if not content:
        return None

    normalized = message.lower()
    no_memory = any(
        marker in normalized
        for marker in (
            "don't save",
            "dont save",
            "do not save",
            "without saving",
            "not save this",
            "don't keep",
            "dont keep",
            "do not keep",
        )
    )
    save_as_memory = False if no_memory else _should_save_reminder_as_memory(message=message, content=content)
    return ReminderIntent(
        due_at=due_at,
        content=content,
        save_as_memory=save_as_memory,
        time_phrase=time_phrase,
    )


def _should_save_reminder_as_memory(*, message: str, content: str) -> bool:
    normalized_message = message.lower()
    normalized_content = content.lower()
    words = re.findall(r"[a-z0-9']+", content)

    explicit_memory_markers = (
        "save this",
        "save it",
        "save as memory",
        "keep this",
        "remember this",
        "don't want to forget",
        "dont want to forget",
        "revisit this note",
        "revisit the note",
        "read this",
        "watch this",
    )
    if any(marker in normalized_message for marker in explicit_memory_markers) and len(words) >= 8:
        return True

    utility_markers = (
        "take water",
        "drink water",
        "call ",
        "message ",
        "email ",
        "meeting",
        "buy ",
        "pay ",
        "submit ",
        "check ",
        "wake ",
        "stand up",
        "stretch",
    )
    if len(words) <= 12 and any(marker in normalized_content for marker in utility_markers):
        return False

    if "http://" in normalized_content or "https://" in normalized_content:
        return True

    durable_markers = (
        "principle",
        "claim",
        "idea",
        "lesson",
        "framework",
        "evidence",
        "source",
        "article",
        "video",
        "book",
        "distribution",
        "product",
        "leadership",
        "startup",
        "founder",
    )
    if len(words) >= 12 and any(marker in normalized_content for marker in durable_markers):
        return True

    return len(words) >= 28


def _parse_due_time(message: str) -> tuple[datetime | None, str | None]:
    normalized = message.lower()
    relative_match = re.search(
        r"\b(in\s+the\s+next|in|within|after|next)\s+"
        r"(\d+)\s*"
        r"(hours?|hrs?|hr|h|minutes?|mins?|min|m|days?|d)\b",
        normalized,
    )
    if relative_match:
        amount = int(relative_match.group(2))
        unit = relative_match.group(3)
        if unit.startswith(("h", "hr")) or unit.startswith("hour"):
            delta = timedelta(hours=amount)
        elif unit.startswith(("m", "min")) or unit.startswith("minute"):
            delta = timedelta(minutes=amount)
        else:
            delta = timedelta(days=amount)
        return utc_now() + delta, message[relative_match.start() : relative_match.end()]

    if "tomorrow" in normalized:
        return utc_now() + timedelta(days=1), "tomorrow"
    return None, None


def _reminder_content(*, message: str, time_phrase: str) -> str:
    lines = [line.strip() for line in message.splitlines()]
    if len(lines) > 1:
        note = "\n".join(line for line in lines[1:] if line).strip()
        if note:
            return note

    without_time = message.replace(time_phrase, " ")
    without_memory_clause = re.sub(
        r"(?i),?\s*but\s+(?:do\s+not|don't|dont)\s+(?:save|keep).*$",
        " ",
        without_time,
    )
    cleaned = re.sub(
        r"(?i)\b(?:please\s+)?(?:set\s+a\s+)?reminder\s+(?:for\s+me\s+)?(?:to\s+)?",
        " ",
        without_memory_clause,
    )
    cleaned = re.sub(r"(?i)\b(?:can|could|would)\s+you\s+", " ", cleaned)
    cleaned = re.sub(r"(?i)\bremind\s+me\s+(?:to\s+)?", " ", cleaned)
    cleaned = re.sub(r"(?i)\btime\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" .,:;?")


def _deterministic_route(message: str, *, history: list[ConversationTurn]) -> ChatRoute | None:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    words = re.findall(r"[a-z0-9']+", normalized)
    pending_url = _pending_url_from_history(history)

    if _is_forget_command(normalized):
        return ChatRoute(
            action="forget",
            reason="The user is asking to archive, forget, or stop surfacing memory.",
        )

    if _is_reminder_command(normalized):
        return ChatRoute(
            action="reminder",
            reason="The user is asking for time-based resurfacing.",
        )

    if _looks_like_self_question(normalized):
        return ChatRoute(
            action="self",
            reason="The user is asking what Crowscap is or what it can do.",
        )

    if _is_save_previous_response_command(message):
        return ChatRoute(
            action="capture",
            reason="The user asked to save the previous assistant response.",
        )

    if pending_url is not None and _is_pending_url_rejection(message):
        return ChatRoute(
            action="conversation",
            reply="No problem. I will leave that link unsaved.",
            reason="The user declined a pending link capture.",
        )

    if _should_capture_pending_url(message, pending_url=pending_url) or _is_url_capture_confirmation(message):
        if pending_url is not None:
            return ChatRoute(
                action="capture",
                reason="The user confirmed that a previously pasted link should be saved.",
            )
        if _is_save_previous_response_command(message):
            return ChatRoute(
                action="capture",
                reason="The user asked to save the previous assistant response.",
            )
        return ChatRoute(
            action="conversation",
            reply="I do not see a pending link in this chat. Send the link again with \"save this\" and I will capture it.",
            reason="The user appears to confirm a link capture, but there is no pending link.",
        )

    if is_explicit_preference_statement(message):
        return ChatRoute(
            action="acknowledge",
            reason="The user explicitly stated a durable preference for how Crowscap should behave.",
        )

    if clarification_reply := _short_contextual_clarification_reply(message, history=history):
        return ChatRoute(
            action="conversation",
            reply=clarification_reply,
            reason="The user is answering a clarification question inside the current conversation.",
        )

    explicit_capture_starts = (
        "remember ",
        "save ",
        "keep ",
        "note ",
        "i learned ",
        "i learnt ",
        "i want to remember ",
    )
    if normalized.startswith(explicit_capture_starts):
        return ChatRoute(action="capture", reason="The user explicitly asked to preserve information.")

    if "http://" in normalized or "https://" in normalized or len(message) >= 500:
        return ChatRoute(action="capture", reason="The message is a source or substantial learning fragment.")

    if any(marker in normalized for marker in SESSION_CONVERSATION_MARKERS):
        return ChatRoute(
            action="conversation",
            reason="The user is asking about the current conversation, not saved knowledge.",
        )

    if _is_explicit_belief_audit_query(normalized):
        return ChatRoute(
            action="audit",
            reason="The user explicitly asked Crowscap to audit or challenge a belief.",
        )

    if _is_explicit_memory_query(normalized):
        return ChatRoute(
            action="answer",
            reason="The user explicitly asked to use saved memories.",
        )

    conversation_openers = (
        "lets talk about ",
        "let's talk about ",
        "talk to me about ",
        "i want to talk about ",
        "can we talk about ",
    )
    if normalized.startswith(conversation_openers):
        return ChatRoute(
            action="conversation",
            reason="The user is opening a normal conversation topic.",
        )

    acknowledgement_words = {
        "ok",
        "okay",
        "alright",
        "cool",
        "great",
        "thanks",
        "thank",
        "you",
        "got",
        "it",
        "understood",
        "sense",
        "makes",
        "this",
        "that",
        "so",
        "much",
        "really",
        "appreciate",
        "appreciated",
        "exactly",
        "clear",
        "understand",
        "i",
        "helpful",
        "perfect",
        "nice",
        "yes",
        "yeah",
        "yep",
    }
    if words and len(words) <= 12 and set(words).issubset(acknowledgement_words):
        return ChatRoute(
            action="acknowledge",
            reply="You are welcome. I am glad it makes sense.",
            reason="The message is a short acknowledgement and contains no learning to store.",
        )

    if words and len(words) <= 4 and any(_is_greeting_word(word) for word in words):
        return ChatRoute(
            action="acknowledge",
            reply="Hey. What are you thinking about?",
            reason="The message is conversational greeting.",
        )

    return None


def _stabilize_route_for_local_context(
    *,
    route: ChatRoute,
    message: str,
    history: list[ConversationTurn],
    pending_url: str | None,
) -> ChatRoute:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if route.action in {"answer", "capture"} and _is_local_conversation_question(
        message=message,
        history=history,
    ):
        logger.info(
            "\U0001f9ed chat.route.stabilized from=%s to=conversation reason=local_context_question",
            route.action,
        )
        return ChatRoute(
            action="conversation",
            reply=None,
            reason="The user is asking a local follow-up, not a saved-memory question.",
        )

    if (
        route.action == "capture"
        and pending_url is None
        and _is_generic_affirmation(message)
        and not _is_save_previous_response_command(message)
    ):
        logger.info(
            "\U0001f9ed chat.route.stabilized from=capture to=conversation reason=orphan_confirmation"
        )
        return ChatRoute(
            action="conversation",
            reply=(
                "I need the actual content before I can save it. Send the note, source, or link you want kept."
            ),
            reason="The user confirmed something, but there is no pending app action.",
        )

    if route.action == "capture" and pending_url is not None and _is_pending_url_rejection(message):
        return ChatRoute(
            action="conversation",
            reply="No problem. I will leave that link unsaved.",
            reason="The user declined a pending link capture.",
        )

    return route


def _is_greeting_word(word: str) -> bool:
    greeting_words = {"hello", "hi", "hey", "yo", "morning", "afternoon", "evening"}
    return word in greeting_words or re.fullmatch(r"he+y+|hello+", word) is not None


def _short_contextual_clarification_reply(
    message: str,
    *,
    history: list[ConversationTurn],
) -> str | None:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    words = re.findall(r"[a-z0-9']+", normalized)
    if not words or len(words) > 8:
        return None
    if not _previous_assistant_asked_for_clarification(history):
        return None

    clarification_markers = (
        "it is ",
        "it's ",
        "its ",
        "that is ",
        "that's ",
        "a ",
        "an ",
    )
    if not normalized.startswith(clarification_markers):
        return None

    return f"Got it — {message.strip().strip('.!?')}. What would you like to do with it?"


def _previous_assistant_asked_for_clarification(history: list[ConversationTurn]) -> bool:
    clarification_markers = (
        "could you clarify",
        "can you clarify",
        "share more context",
        "what is it",
        "what it is",
        "is it a",
        "what would you like",
    )
    for turn in reversed(history[-4:]):
        if turn.role != "assistant":
            continue
        content = re.sub(r"\s+", " ", turn.content.strip().lower())
        if any(marker in content for marker in clarification_markers):
            return True
    return False


def _is_forget_command(normalized: str) -> bool:
    if "what am i forgetting" in normalized:
        return False
    if (
        any(marker in normalized for marker in ("don't show me weak", "dont show me weak", "do not show me weak"))
        and any(marker in normalized for marker in ("evidence", "source", "corroborated"))
    ):
        return False
    forget_markers = (
        "can you forget",
        "forget what i know",
        "forget what know",
        "forget my memories",
        "forget memories",
        "archive memory",
        "archive memories",
        "archive the pdf",
        "archive what you just saved",
        "archive the last thing you saved",
        "delete memory",
        "delete what you just saved",
        "delete the last thing you saved",
        "delete the pdf",
        "delete that",
        "remove memory",
        "remove memories",
        "remove what you just saved",
        "remove the last thing you saved",
        "remove the pdf",
        "remove that",
        "don't show me",
        "dont show me",
        "do not show me",
        "stop reminding me",
    )
    return any(marker in normalized for marker in forget_markers)


def _is_reminder_command(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            "remind me",
            "set a reminder",
            "reminder for me",
        )
    )


def _looks_like_self_question(normalized: str) -> bool:
    words = set(re.findall(r"[a-z0-9']+", normalized))
    if not words:
        return False
    self_terms = {"you", "u", "yourself", "crowscap", "app", "product", "tool", "system"}
    capability_terms = {"do", "does", "save", "keep", "remember", "help", "use", "purpose", "work", "built"}
    if not words.intersection(self_terms):
        return False
    if _is_explicit_memory_query(normalized) or _is_explicit_belief_audit_query(normalized):
        return False
    if normalized.startswith(("what ", "who ", "why ", "how ", "can ", "could ", "explain ", "tell me ")):
        return bool(words.intersection(capability_terms) or {"what", "who", "why", "how"}.intersection(words))
    return any(
        marker in normalized
        for marker in (
            "i don't understand this app",
            "i dont understand this app",
            "what is this app",
            "what are you",
            "what is you",
            "what are u",
            "who are you",
            "who are u",
        )
    )


def _is_explicit_memory_query(normalized: str) -> bool:
    memory_markers = (
        "what do i know",
        "what have i saved",
        "what did i save",
        "what have i learned",
        "what have i learnt",
        "what did i learn",
        "what did i learn",
        "search my memory",
        "search memories",
        "search my saved",
        "my saved",
        "saved memory",
        "saved memories",
        "my memory",
        "my memories",
        "do i have any notes",
        "from my notes",
        "based on my notes",
        "based on what i saved",
        "based on my saved",
        "what does crowscap know",
        "what am i forgetting",
    )
    return any(marker in normalized for marker in memory_markers)


def _should_probe_memory_for_conversation(
    *,
    message: str,
    history: list[ConversationTurn],
) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if _is_explicit_memory_query(normalized):
        return True
    if _is_local_conversation_question(message=message, history=history):
        logger.info(
            "\U0001f9ed chat.conversation.memory_probe_skipped reason=local_context_question"
        )
        return False
    if _is_short_conversation_followup(normalized):
        logger.info(
            "\U0001f9ed chat.conversation.memory_probe_skipped reason=short_followup"
        )
        return False
    words = re.findall(r"[a-z0-9']+", normalized)
    if len(words) >= 8 or re.match(r"^(?:how|why|should|can|could)\b", normalized):
        return True
    return False


def _is_local_conversation_question(
    *,
    message: str,
    history: list[ConversationTurn],
) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if _first_url(message):
        return False
    if _is_explicit_memory_query(normalized) or _is_explicit_belief_audit_query(normalized):
        return False
    if any(marker in normalized for marker in SESSION_CONVERSATION_MARKERS):
        return True
    if _is_definition_or_meaning_question(normalized):
        return True
    if _is_short_conversation_followup(normalized) and _has_recent_context(history):
        return True
    return False


def _is_definition_or_meaning_question(normalized: str) -> bool:
    if any(marker in normalized for marker in ("my memory", "my memories", "saved", "notes", "source")):
        return False
    patterns = (
        r"^what\s+(?:is|does|do)\s+.{1,80}\??$",
        r"^what\s+is\s+.{1,80}\s+mean\??$",
        r"^what\s+does\s+.{1,80}\s+mean\??$",
        r"^meaning\s+of\s+.{1,80}\??$",
        r"^define\s+.{1,80}\??$",
        r"^explain\s+the\s+word\s+.{1,80}\??$",
    )
    if not any(re.fullmatch(pattern, normalized) is not None for pattern in patterns):
        return False
    words = re.findall(r"[a-z0-9']+", normalized)
    return len(words) <= 10


def _is_short_conversation_followup(normalized: str) -> bool:
    if _is_explicit_memory_query(normalized):
        return False
    words = re.findall(r"[a-z0-9']+", normalized)
    if not words or len(words) > 10:
        return False
    followup_patterns = (
        r"^(?:do|dont|don't)\s+you\s+think\??$",
        r"^what\s+do\s+you\s+think\??$",
        r"^why\??$",
        r"^why\s+is\s+that\??$",
        r"^how\s+so\??$",
        r"^what\s+do\s+you\s+mean\??$",
        r"^what\s+is\s+that\??$",
        r"^what\s+does\s+that\s+mean\??$",
        r"^can\s+you\s+explain\s+that\??$",
        r"^go\s+deeper\??$",
        r"^tell\s+me\s+more\??$",
    )
    return any(re.fullmatch(pattern, normalized) is not None for pattern in followup_patterns)


def _has_recent_context(history: list[ConversationTurn]) -> bool:
    return any(turn.content.strip() for turn in history[-4:])


def _is_explicit_belief_audit_query(normalized: str) -> bool:
    audit_markers = (
        "audit what i believe",
        "audit my belief",
        "audit my beliefs",
        "belief audit",
        "challenge what i believe",
        "challenge my belief",
        "challenge my beliefs",
        "evidence check",
        "check my belief",
        "check what i believe",
        "is what i believe",
        "is what i know about",
        "how reliable is what i know",
        "how reliable are my notes",
        "compare my belief with public evidence",
        "compare what i saved with public evidence",
        "do i have good evidence",
    )
    return any(marker in normalized for marker in audit_markers)


def _audit_topic_from_message(message: str) -> str:
    compact = re.sub(r"\s+", " ", message.strip())
    normalized = compact.lower()
    prefixes = (
        "audit what i believe about ",
        "audit what i know about ",
        "audit my belief about ",
        "audit my beliefs about ",
        "belief audit on ",
        "belief audit about ",
        "challenge what i believe about ",
        "challenge my belief about ",
        "challenge my beliefs about ",
        "evidence check on ",
        "evidence check about ",
        "check my belief about ",
        "check what i believe about ",
        "is what i believe about ",
        "is what i know about ",
        "how reliable is what i know about ",
        "compare my belief with public evidence on ",
        "compare what i saved with public evidence on ",
        "do i have good evidence for ",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return compact[len(prefix) :].strip(" ?.,;:") or compact
    return compact


def _first_url(message: str) -> str | None:
    match = re.search(r"https?://[^\s)>\]]+", message)
    if not match:
        return None
    return match.group(0).rstrip(".,;:")


def _message_without_url(message: str, url: str) -> str:
    return re.sub(r"\s+", " ", message.replace(url, " ")).strip()


def _message_without_urls(message: str) -> str:
    without_urls = re.sub(r"https?://[^\s)>\]]+", " ", message)
    without_empty_markdown = re.sub(r"\[\s*\]\s*\(\s*\)", " ", without_urls)
    return re.sub(r"\s+", " ", without_empty_markdown).strip(" .,:;")


def _should_capture_mixed_url_message_as_text(message: str) -> bool:
    if _has_explicit_url_capture_intent(message):
        return False
    text_without_urls = _message_without_urls(message)
    words = re.findall(r"[a-z0-9']+", text_without_urls.lower())
    return len(words) >= 18 or len(text_without_urls) >= 120


def _is_substantial_direct_capture(message: str) -> bool:
    stripped = message.strip()
    words = re.findall(r"[a-z0-9']+", stripped.lower())
    return len(stripped) >= MIN_DIRECT_TEXT_CAPTURE_CHARS and len(words) >= 3


def _has_explicit_url_capture_intent(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    intent_markers = (
        "save this",
        "save the",
        "save it",
        "save link",
        "save this link",
        "remember this",
        "remember the",
        "capture this",
        "capture the",
        "keep this",
        "keep the",
        "store this",
        "store the",
        "add this to memory",
        "add to memory",
        "read this",
        "read later",
        "watch later",
        "process this",
        "extract this",
        "summarize this",
        "summarise this",
        "analyze this",
        "analyse this",
        "learn from this",
    )
    return any(marker in normalized for marker in intent_markers)


def _is_reference_only_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().strip(".")
    reference_hosts = {
        "chat.whatsapp.com",
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "fb.watch",
        "instagram.com",
        "www.instagram.com",
        "x.com",
        "www.x.com",
        "twitter.com",
        "www.twitter.com",
        "tiktok.com",
        "www.tiktok.com",
    }
    return host in reference_hosts or host.endswith(".facebook.com") or host.endswith(".instagram.com")


def _create_reference_link_capture(
    *,
    db: Session,
    url: str,
    intent_text: str | None,
    embedder: MemoryEmbedder,
    user_id: str | None,
) -> TextCaptureResponse:
    clean_intent = _clean_reference_link_intent(intent_text)
    title = _reference_link_title(url)
    raw_text = f"Reference link: {url}"
    if clean_intent:
        raw_text += f"\nWhy it matters: {clean_intent}"

    memory_content = (
        f"Saved reference link for: {clean_intent}\nLink: {url}"
        if clean_intent
        else f"Saved reference link: {url}"
    )
    embedding = embedder.embed_texts([memory_content])[0]
    content_hash = hashlib.sha256(f"{user_id or 'anon'}:{url}:{clean_intent or ''}".encode("utf-8")).hexdigest()

    source = Source(
        user_id=user_id,
        source_type="reference",
        original_url=url,
        resolved_url=url,
        title=title,
        raw_text=raw_text,
        extracted_text_hash=content_hash,
        metadata_json={
            "input_kind": "reference_link",
            "reference_only": True,
            "reason": clean_intent,
        },
    )
    db.add(source)
    db.flush()

    capture = Capture(
        user_id=user_id,
        source_id=source.id,
        user_note=clean_intent,
        user_intent_text=clean_intent,
        inferred_intents=["reference"],
        status="ready",
    )
    db.add(capture)
    db.flush()

    memory = Memory(
        user_id=user_id,
        source_id=source.id,
        capture_id=capture.id,
        memory_type="reference",
        epistemic_label="source_summary",
        content=memory_content,
        summary=clean_intent or "Saved reference link",
        confidence="high" if clean_intent else "medium",
        confidence_reason=(
            "The user gave a reason for keeping this reference."
            if clean_intent
            else "The user confirmed this link should be kept as a reference."
        ),
        source_strength="unknown",
        embedding_json=embedding,
        next_review_at=initial_next_review_at(memory_confidence="medium"),
        review_count=0,
        recall_score=0.5,
    )
    db.add(memory)
    db.flush()
    update_memory_embedding_vector(db=db, memory_id=memory.id, embedding=embedding)
    db.commit()

    return TextCaptureResponse(
        capture_id=capture.id,
        source_id=source.id,
        source_type=source.source_type,
        source_title=source.title,
        original_content=source.raw_text,
        status=capture.status,
        inferred_intents=["reference"],
        memories=[
            MemoryCardResponse(
                id=memory.id,
                source_type=source.source_type,
                memory_type="reference",
                epistemic_label="source_summary",
                content=memory.content,
                summary=memory.summary,
                confidence=memory.confidence,
                confidence_reason=memory.confidence_reason,
                source_strength=memory.source_strength,
                embedding_dimensions=len(embedding),
                relationships=[],
            )
        ],
    )


def _url_ingestion_failure_response(*, url: str, error_message: str) -> ChatResponse:
    return ChatResponse(
        action="conversation",
        message=(
            f"I could not read this link: {url}\n\n"
            f"{error_message}\n\n"
            "I have not saved it yet. If the link still matters, tell me to save it as a reference "
            "and I will keep the URL without pretending I read the content."
        ),
        saved=False,
        next_step="You can also paste the important point from the link and I will save that instead.",
    )


def _clean_reference_link_intent(intent_text: str | None) -> str | None:
    if not intent_text:
        return None
    cleaned = re.sub(r"\s+", " ", intent_text.strip()).strip(" .,:;!?")
    cleaned = re.sub(
        r"^(?:yes|yeah|yep|sure|ok|okay|alright|please|save|capture|remember|keep|read|process|ingest|handle|it|this|link|the)+\b",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;!?")
    return cleaned[:300] or None


def _reference_link_title(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "link").lower().removeprefix("www.")
    if host == "chat.whatsapp.com":
        return "WhatsApp invite link"
    if "facebook.com" in host or host == "fb.watch":
        return "Facebook reference link"
    if "instagram.com" in host:
        return "Instagram reference link"
    if host in {"x.com", "twitter.com"}:
        return "Social reference link"
    return f"Reference from {host}"


def _pending_link_confirmation_intent(message: str) -> str | None:
    if _is_generic_affirmation(message) or _is_url_capture_confirmation(message):
        return None
    return message


def _is_url_capture_confirmation(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    confirmation_phrases = {
        "save it",
        "save it anyway",
        "save it then",
        "save it as reference",
        "save it as a reference",
        "save this link",
        "save this link anyway",
        "save this link as reference",
        "save this link as a reference",
        "yes save it",
        "yes save this link",
        "yeah save it",
        "yep save it",
        "capture it",
        "capture this link",
        "remember it",
        "remember this link",
        "read it",
        "read this link",
        "process it",
        "process this link",
    }
    if normalized in confirmation_phrases:
        return True

    command_patterns = (
        r"^(?:please\s+)?(?:save|capture|remember|read|process|ingest)\s+(?:it|this|the\s+link)(?:\s+(?:anyway|then|as\s+(?:a\s+)?reference))?(?:\s+please)?$",
        r"^(?:yes|yeah|yep|sure|ok|okay|alright)\s*,?\s*(?:please\s+)?(?:save|capture|remember|read|process|ingest)\s+(?:it|this|the\s+link)(?:\s+(?:anyway|then|as\s+(?:a\s+)?reference))?(?:\s+please)?$",
    )
    return any(re.fullmatch(pattern, normalized) is not None for pattern in command_patterns)


def _should_save_pending_url_as_reference_after_failed_read(
    message: str,
    *,
    history: list[ConversationTurn],
) -> bool:
    if not _recent_assistant_reported_url_read_failure(history):
        return False
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if re.search(r"\b(?:try again|retry|read it|process it|extract it)\b", normalized):
        return False
    if not re.search(r"\b(?:save|keep|remember|store|capture)\b", normalized):
        return False
    return bool(
        re.search(r"\b(?:it|this|that|link|url|video|short|source|reference)\b", normalized)
        or re.search(r"\b(?:anyway|then)\b", normalized)
    )


def _recent_assistant_reported_url_read_failure(history: list[ConversationTurn]) -> bool:
    for turn in reversed(history[-6:]):
        content = re.sub(r"\s+", " ", turn.content.strip().lower())
        if turn.role == "assistant" and (
            "i could not read this link" in content
            or "crowscap could not read this youtube" in content
            or "could not read this youtube" in content
            or "could not read the link" in content
        ):
            return True
        if turn.role == "assistant" and ("i kept this as" in content or "i kept this link as" in content):
            return False
    return False


def _is_generic_affirmation(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if not normalized:
        return False
    if re.search(r"\b(?:no|not|dont|don't|never|cancel|ignore|stop)\b", normalized):
        return False
    affirmative_patterns = (
        r"^(?:yes|yeah|yep|yup|sure|ok|okay|alright|do it|go ahead)(?:\s+please)?$",
        r"^(?:yes|yeah|yep|sure|ok|okay|alright),?\s*(?:please|go ahead|do it)$",
        r"^(?:please\s+)?(?:go ahead|do it)$",
    )
    return any(re.fullmatch(pattern, normalized) is not None for pattern in affirmative_patterns)


def _is_pending_url_rejection(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    rejection_patterns = (
        r"^(?:no|nope|nah)(?:\s+thanks|\s+thank\s+you)?$",
        r"^(?:do not|don't|dont)\s+(?:save|capture|remember|read|process)\s+(?:it|this|the\s+link)$",
        r"^(?:cancel|ignore|leave)\s+(?:it|this|the\s+link)(?:\s+unsaved)?$",
    )
    return any(re.fullmatch(pattern, normalized) is not None for pattern in rejection_patterns)


def _should_capture_pending_url(
    message: str,
    *,
    pending_url: str | None,
    route: ChatRoute | None = None,
) -> bool:
    if pending_url is None:
        return False
    if _first_url(message):
        return False
    if _is_pending_url_rejection(message):
        return False
    if _is_url_capture_confirmation(message) or _is_generic_affirmation(message):
        return True
    return route is not None and route.action == "capture" and _looks_like_pending_url_reply(message)


def _looks_like_pending_url_reply(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    words = re.findall(r"[a-z0-9']+", normalized)
    if not words:
        return False

    # This is only used after the semantic router classified the message as capture.
    # It keeps a pending link from swallowing a brand-new long note.
    pending_references = {
        "it",
        "this",
        "that",
        "link",
        "url",
        "video",
        "short",
        "shorts",
        "article",
        "page",
        "source",
        "read",
        "process",
        "save",
        "capture",
        "remember",
        "ingest",
        "handle",
        "open",
        "check",
        "thing",
        "one",
    }
    if any(word in pending_references for word in words):
        return len(words) <= 28
    if len(words) <= 10 and re.search(
        r"\b(?:yes|yeah|yep|yup|sure|ok|okay|alright|absolutely|definitely|fine|please)\b",
        normalized,
    ):
        return True
    return False


def _is_save_previous_response_command(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", message.strip().lower()).strip(" .!?")
    if _first_url(message):
        return False

    phrases = {
        "save that",
        "save this",
        "save it",
        "remember that",
        "remember this",
        "remember it",
        "keep that",
        "keep this",
        "keep it",
        "store that",
        "store this",
        "store it",
        "save your answer",
        "save your response",
        "save your reply",
        "save what you just said",
        "save your last answer",
        "save your previous answer",
        "save the last answer",
        "save the previous answer",
        "save the last response",
        "save the previous response",
        "save the last reply",
        "save the previous reply",
        "remember your answer",
        "remember your response",
        "remember your reply",
        "remember what you just said",
        "keep your answer",
        "keep your response",
        "keep your reply",
        "keep what you just said",
        "store your answer",
        "store your response",
        "store your reply",
        "store what you just said",
    }
    if normalized in phrases:
        return True
    patterns = (
        r"^save\s+(?:that|this|it)\s+(?:to|in|into)\s+(?:my\s+)?memory$",
        r"^remember\s+(?:that|this|it)\s+(?:for\s+me)?$",
        r"^keep\s+(?:that|this|it)\s+(?:for\s+me)?$",
        r"^(?:save|remember|keep|store)\s+(?:the\s+)?(?:answer|reply|response)\s+(?:you\s+)?(?:just\s+)?(?:gave|sent|wrote|said)(?:\s+me)?$",
        r"^(?:save|remember|keep|store)\s+what\s+you\s+just\s+(?:said|wrote|sent|answered)$",
        r"^(?:save|remember|keep|store)\s+(?:your|the)\s+(?:last|previous)\s+(?:answer|reply|response)$",
    )
    if any(re.fullmatch(pattern, normalized) is not None for pattern in patterns):
        return True
    if _is_short_previous_response_save_command(normalized):
        return True

    if not re.search(r"\b(?:save|remember|keep|store)\b", normalized):
        return False
    if not (
        re.search(r"\b(?:that|this|it)\b", normalized)
        or re.search(r"\b(?:answer|reply|response)\b", normalized)
        or "what you just" in normalized
    ):
        return False

    words = re.findall(r"[a-z0-9']+", normalized)
    command_words = {
        "a",
        "about",
        "alright",
        "answer",
        "answered",
        "awesome",
        "can",
        "cool",
        "could",
        "for",
        "gave",
        "go",
        "it",
        "just",
        "keep",
        "last",
        "me",
        "memory",
        "my",
        "nice",
        "ok",
        "okay",
        "one",
        "please",
        "previous",
        "reply",
        "remember",
        "response",
        "said",
        "save",
        "sent",
        "store",
        "that",
        "the",
        "this",
        "to",
        "u",
        "what",
        "would",
        "wrote",
        "yeah",
        "yep",
        "yes",
        "you",
        "your",
    }
    return len(words) <= 16 and set(words).issubset(command_words)


def _is_short_previous_response_save_command(normalized: str) -> bool:
    words = re.findall(r"[a-z0-9']+", normalized)
    if not words or len(words) > 18:
        return False

    save_verbs = {"save", "remember", "keep", "store"}
    pointers = {"that", "this", "it"}
    response_words = {"answer", "reply", "response"}
    allowed_after_pointer = {
        "for",
        "me",
        "please",
        "pls",
        "plz",
        "to",
        "in",
        "into",
        "my",
        "memory",
        "later",
        "now",
    }
    allowed_after_response = allowed_after_pointer | {"you", "just", "gave", "sent", "wrote", "said", "answered"}

    for verb_index, word in enumerate(words):
        if word not in save_verbs:
            continue
        # Casual prefixes are normal: "hmm save that", "cool save that", "can you save that".
        if verb_index > 5:
            continue
        tail = words[verb_index + 1 :]
        for pointer_index, pointer in enumerate(tail[:5]):
            if pointer not in pointers:
                continue
            rest = tail[pointer_index + 1 :]
            return all(word in allowed_after_pointer for word in rest)
        for response_index, response_word in enumerate(tail[:6]):
            if response_word not in response_words:
                continue
            rest = tail[response_index + 1 :]
            return all(word in allowed_after_response for word in rest)
    return False


def _pending_url_from_history(history: list[ConversationTurn]) -> str | None:
    assistant_asked_confirmation = False
    for turn in reversed(history[-8:]):
        if turn.role == "assistant" and (
            "I will leave that link unsaved" in turn.content
            or "I kept this as" in turn.content
            or "I kept this link as" in turn.content
            or "Nothing has been saved from this link" in turn.content
        ):
            return None
        if turn.role == "assistant" and "I have not saved it yet" in turn.content:
            assistant_asked_confirmation = True
            continue
        if turn.role != "user":
            continue
        url = _first_url(turn.content)
        if not url:
            continue
        if assistant_asked_confirmation or not _has_explicit_url_capture_intent(turn.content):
            return url
    return None


def _url_capture_confirmation_prompt(*, url: str) -> str:
    if _is_reference_only_url(url):
        return (
            f"I found this link: {url}\n\n"
            "I have not saved it yet. This kind of link is usually best kept as a reference. "
            "If it matters, tell me what to remember it for, or say \"save it\" and I will keep the link."
        )
    return (
        f"I found this link: {url}\n\n"
        "I have not saved it yet. If this is something you want in memory, reply "
        "\"save this link\" and I will keep the important ideas from it. "
        "If it was accidental, you can ignore this and keep chatting."
    )


def _retrieval_query(*, message: str, history: list[ConversationTurn]) -> str:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    follow_up_phrases = {
        "tell me more",
        "explain more",
        "why",
        "why is that",
        "how so",
        "what else",
        "go deeper",
        "continue",
    }
    if normalized not in follow_up_phrases and len(normalized.split()) > 4:
        return message

    previous_user_turn = next(
        (turn.content for turn in reversed(history) if turn.role == "user"),
        None,
    )
    if previous_user_turn is None:
        return message
    return f"{previous_user_turn}\nFollow-up question: {message}"


def _capture_confirmation(capture) -> str:
    if getattr(capture, "source_type", None) == "reference":
        return "I kept this link as a reference."

    comparison_count = sum(
        1
        for memory in capture.memories
        for relation in memory.relationships
        if relation.relationship_type in {"conflicts", "tension", "qualifies"}
    )
    if comparison_count:
        message = (
            f"I kept this as {len(capture.memories)} memories and found "
            f"{comparison_count} idea{'s' if comparison_count != 1 else ''} "
            "worth comparing with something you saved before."
        )
    else:
        message = f"I kept this as {len(capture.memories)} distinct memories."

    if _capture_contains_redactions(capture):
        message += "\n\nI removed personal identifiers before saving, so your memory keeps the idea without exposing contact details."

    return message


def _capture_contains_redactions(capture) -> bool:
    original = getattr(capture, "original_content", None) or ""
    return any(
        placeholder in original
        for placeholder in ("[email]", "[phone number]", "[government id]", "[address]")
    )


def _relation_context_for_results(*, db: Session, memory_ids: list[str]) -> list[str]:
    if not memory_ids:
        return []

    relations = list(
        db.scalars(
            select(MemoryRelation).where(
                or_(
                    MemoryRelation.source_memory_id.in_(memory_ids),
                    MemoryRelation.target_memory_id.in_(memory_ids),
                )
            )
        ).all()
    )
    related_ids = {
        relation.source_memory_id for relation in relations
    } | {
        relation.target_memory_id for relation in relations
    }
    memories = {
        memory.id: memory
        for memory in db.scalars(select(Memory).where(Memory.id.in_(related_ids))).all()
    }

    context: list[str] = []
    for relation in relations[:12]:
        source = memories.get(relation.source_memory_id)
        target = memories.get(relation.target_memory_id)
        if source is None or target is None:
            continue
        context.append(
            f"{relation.relation_type} ({relation.strength}): "
            f"'{source.content}' <-> '{target.content}'. "
            f"Reason: {relation.explanation or 'No explanation stored.'}"
        )
    return context


# Prompt templates and builder functions are in chat_prompts.py (pure, testable).
from app.services.chat_prompts import (
    CHAT_ROUTER_SYSTEM_PROMPT,
    CHAT_SYNTHESIS_SYSTEM_PROMPT,
    CHAT_CONVERSATION_SYSTEM_PROMPT,
    _build_router_prompt,
    _build_synthesis_prompt,
    _build_conversation_prompt,
)
