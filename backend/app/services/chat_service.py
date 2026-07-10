from __future__ import annotations

import re
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import ChatRoute, ConversationalChatReply, GroundedChatSynthesis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import ChatMessage, Conversation, Memory, MemoryRelation, utc_now
from app.schemas.belief import BeliefAuditRequest
from app.schemas.capture import TextCaptureRequest, UrlCaptureRequest
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ConversationTurn,
)
from app.schemas.search import SearchRequest, SearchResponse
from app.services.belief_audit_service import BeliefAuditor
from app.services.capture_service import create_text_capture
from app.services.embedding_service import MemoryEmbedder
from app.services.extraction_service import MemoryExtractor
from app.services.ingestion_service import create_pdf_capture_from_bytes, create_url_capture
from app.services.relationship_service import MemoryRelationDetector
from app.services.search_service import search_memories

logger = get_logger("services.chat")

MEMORY_QUERY_MIN_SCORE = 0.25
CONVERSATION_MEMORY_MIN_SCORE = 0.55
SESSION_CONVERSATION_MARKERS = (
    "in this chat",
    "this chat",
    "this conversation",
    "current chat",
    "this session",
    "earlier here",
    "earlier in chat",
    "earlier in this chat",
    "have i thanked",
    "did i thank",
    "what did i just say",
    "what was my last message",
    "last message",
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
    ) -> GroundedChatSynthesis:
        pass


class ChatConversationResponder(Protocol):
    def respond(self, *, message: str, history: list[ConversationTurn]) -> str:
        pass


class QwenChatIntentRouter:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()
        self.settings = get_settings()

    def route(self, *, message: str, history: list[ConversationTurn]) -> ChatRoute:
        deterministic = _deterministic_route(message)
        if deterministic is not None:
            logger.info(
                "\U0001f9ed chat.route.deterministic action=%s chars=%s",
                deterministic.action,
                len(message),
            )
            return deterministic

        payload = self.client.chat_json(
            system_prompt=CHAT_ROUTER_SYSTEM_PROMPT,
            user_prompt=_build_router_prompt(message=message, history=history),
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
    ) -> GroundedChatSynthesis:
        payload = self.client.chat_json(
            system_prompt=CHAT_SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=_build_synthesis_prompt(
                question=question,
                history=history,
                search=search,
                relation_context=relation_context,
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

    def respond(self, *, message: str, history: list[ConversationTurn]) -> str:
        payload = self.client.chat_json(
            system_prompt=CHAT_CONVERSATION_SYSTEM_PROMPT,
            user_prompt=_build_conversation_prompt(message=message, history=history),
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
    persisted_history = _conversation_turns(conversation)
    effective_history = persisted_history or payload.history

    logger.info(
        "\U0001f4ac chat.message.start chars=%s history=%s conversation_id=%s",
        len(payload.message),
        len(effective_history),
        conversation.id,
    )
    route = router.route(message=payload.message, history=effective_history)

    user_message = ChatMessage(
        conversation_id=conversation.id,
        user_id=user_id,
        role="user",
        content=payload.message,
    )
    db.add(user_message)
    db.flush()

    if route.action == "acknowledge":
        reply = route.reply or "You are welcome. I am here when you want to keep going."
        logger.info("\u2705 chat.message.complete action=acknowledge saved=False")
        response = ChatResponse(action="acknowledge", message=reply, saved=False)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "conversation":
        if _is_session_conversation(normalized_message=payload.message.lower()):
            reply = route.reply or _conversation_reply(
                message=payload.message,
                history=effective_history,
            )
        else:
            high_confidence_context = _search_for_conversation_context(
                db=db,
                message=payload.message,
                embedder=embedder,
                user_id=user_id,
            )
            if high_confidence_context.results:
                relation_context = _relation_context_for_results(
                    db=db,
                    memory_ids=[result.memory_id for result in high_confidence_context.results],
                )
                synthesis = synthesizer.synthesize(
                    question=payload.message,
                    history=effective_history,
                    search=high_confidence_context,
                    relation_context=relation_context,
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
                return _persist_assistant_response(
                    db=db,
                    conversation=conversation,
                    user_message=user_message,
                    response=response,
                    user_id=user_id,
                )

            reply = route.reply or conversation_responder.respond(
                message=payload.message,
                history=effective_history,
            )
        logger.info("\u2705 chat.message.complete action=conversation saved=False")
        response = ChatResponse(action="conversation", message=reply, saved=False)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )

    if route.action == "capture":
        if url := _first_url(payload.message):
            intent_text = _message_without_url(payload.message, url)
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
        else:
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
    relation_context = _relation_context_for_results(
        db=db,
        memory_ids=[result.memory_id for result in search.results],
    )
    synthesis = synthesizer.synthesize(
        question=payload.message,
        history=effective_history,
        search=search,
        relation_context=relation_context,
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
        if conversation is not None and (user_id is None or conversation.user_id == user_id):
            return conversation
        logger.info(
            "\U0001f4ac chat.conversation.missing requested_id=%s action=create_new",
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


def _conversation_turns(conversation: Conversation) -> list[ConversationTurn]:
    return [
        ConversationTurn(role=message.role, content=message.content)
        for message in conversation.messages
        if message.role in {"user", "assistant"} and message.content.strip()
    ][-12:]


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
        ],
    )


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


def _is_session_conversation(*, normalized_message: str) -> bool:
    normalized = re.sub(r"\s+", " ", normalized_message.strip())
    return any(marker in normalized for marker in SESSION_CONVERSATION_MARKERS)


def _conversation_reply(*, message: str, history: list[ConversationTurn]) -> str:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    previous_user_turns = [turn.content for turn in history if turn.role == "user"]

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


def _deterministic_route(message: str) -> ChatRoute | None:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    words = re.findall(r"[a-z0-9']+", normalized)

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

    question_starts = (
        "what ",
        "why ",
        "how ",
        "when ",
        "where ",
        "who ",
        "which ",
        "can you ",
        "could you ",
        "would you ",
        "tell me ",
        "show me ",
        "find ",
        "search ",
        "do i ",
        "did i ",
        "have i ",
        "explain ",
    )
    if normalized.endswith("?") or normalized.startswith(question_starts):
        return ChatRoute(
            action="conversation",
            reason="The user is asking a normal question, not explicitly asking for saved memories.",
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

    greeting_words = {"hello", "hi", "hey", "yo", "morning", "afternoon", "evening"}
    if words and len(words) <= 4 and any(word in greeting_words for word in words):
        return ChatRoute(
            action="acknowledge",
            reply="Hey. What are you thinking about?",
            reason="The message is conversational greeting.",
        )

    return None


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
    comparison_count = sum(
        1
        for memory in capture.memories
        for relation in memory.relationships
        if relation.relationship_type in {"conflicts", "tension", "qualifies"}
    )
    if comparison_count:
        return (
            f"I kept this as {len(capture.memories)} memories and found "
            f"{comparison_count} idea{'s' if comparison_count != 1 else ''} "
            "worth comparing with something you saved before."
        )
    return f"I kept this as {len(capture.memories)} distinct memories."


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


def _build_router_prompt(*, message: str, history: list[ConversationTurn]) -> str:
    history_text = "\n".join(
        f"{turn.role}: {turn.content}" for turn in history[-6:]
    ) or "No earlier turns."
    return f"""Classify the user's latest message.

Return JSON:
{{
  "action": "acknowledge" | "conversation" | "capture" | "answer" | "audit",
  "reply": "short natural reply only when action is acknowledge, otherwise null",
  "reason": "brief classification reason"
}}

Definitions:
- acknowledge: greetings, thanks, agreement, confirmation, social replies, or conversational continuation with no durable knowledge to save.
- conversation: the user asks a normal question, asks for advice, opens a topic, asks about this current chat/session, or wants normal assistant continuity without explicitly needing saved memories.
- capture: the user supplies a substantive learning fragment, claim, source, note, reflection, or explicitly asks to remember/save something.
- answer: the user explicitly asks about saved/learned knowledge, asks what they know from memory, asks to search memories/notes, requests comparison across saved memories, or wants help thinking with their knowledge base.
- audit: the user explicitly asks Crowscap to challenge, audit, evidence-check, or compare a belief against public evidence.

Never classify thanks, "okay", "this makes sense", or simple agreement as capture.
Never run saved-memory search for questions about only the current chat, such as "have I thanked you before in this chat?"
Do not classify ordinary advice questions as answer just because they are questions.
Do not classify ordinary memory questions as audit unless the user explicitly asks for an audit, challenge, evidence check, reliability check, or public evidence comparison.
Do not save every user message. Capture only when there is durable informational content or explicit saving intent.

Recent conversation:
{history_text}

Latest user message:
{message}
"""


def _build_synthesis_prompt(
    *,
    question: str,
    history: list[ConversationTurn],
    search: SearchResponse,
    relation_context: list[str],
) -> str:
    history_text = "\n".join(
        f"{turn.role}: {turn.content}" for turn in history[-6:]
    ) or "No earlier turns."
    evidence_text = "\n".join(
        (
            f"[{index}] {result.content}\n"
            f"Source: {result.source_title or 'Untitled source'}; "
            f"type={result.memory_type}; epistemic_label={result.epistemic_label}; "
            f"confidence={result.confidence}; source_strength={result.source_strength}; "
            f"similarity={result.similarity_score}"
        )
        for index, result in enumerate(search.results, start=1)
    ) or "No relevant personal memories were found."
    relations_text = "\n".join(relation_context) or "No stored relationships were found."

    return f"""Answer the user's question as their source-aware second brain.

Return JSON:
{{
  "answer": "a natural, direct answer in 1-4 short paragraphs",
  "knowledge_gaps": ["important missing evidence, context, or understanding"],
  "tensions": ["plain-language description of ideas that disagree or depend on context"],
  "next_step": "one useful question or action, or null"
}}

Rules:
- Synthesize; do not dump or merely list memory cards.
- Make the product's value clear by connecting repeated ideas and explaining what they mean together.
- Treat saved memories as the user's information history, not automatically as objective truth.
- Explicitly notice opinions, advice, weak sources, unsupported claims, and missing evidence.
- If memories disagree, explain the difference and when context changes which idea applies.
- Use plain language for user-facing text. Do not use the word "tension".
- knowledge_gaps should name what the user would need to understand or verify before treating the conclusion as reliable.
- You may use general reasoning to explain a gap, but do not pretend it came from the user's saved sources.
- If no personal memories were found, answer helpfully but clearly say this answer is not grounded in their saved memory yet.
- Do not mention vector scores or internal retrieval.

Recent conversation:
{history_text}

User question:
{question}

Relevant saved memories:
{evidence_text}

Stored relationships:
{relations_text}
"""


def _build_conversation_prompt(*, message: str, history: list[ConversationTurn]) -> str:
    history_text = "\n".join(
        f"{turn.role}: {turn.content}" for turn in history[-8:]
    ) or "No earlier turns."
    return f"""Reply to the user's latest message as Crowscap's normal conversational assistant.

Return JSON:
{{
  "reply": "a natural, useful reply"
}}

Rules:
- This is normal chat, not a saved-memory answer.
- Do not mention saved memories, sources, vector search, recall, or knowledge cards.
- Do not say you saved anything.
- If the user asks for advice, answer directly like a thoughtful assistant.
- Keep the tone warm, clear, and practical.
- If the user asks to save, remember, or remind them, say you can do that when they state exactly what to save or when to remind them.

Recent conversation:
{history_text}

Latest user message:
{message}
"""


CHAT_ROUTER_SYSTEM_PROMPT = """You route messages for Crowscap, a conversational second brain.
Return only valid JSON. Be conservative about saving: ordinary chat must remain ordinary chat."""


CHAT_SYNTHESIS_SYSTEM_PROMPT = """You are Crowscap's source-aware conversational intelligence.
Return only valid JSON. Help the user understand, question, and use what they have learned without creating false certainty."""


CHAT_CONVERSATION_SYSTEM_PROMPT = """You are Crowscap's normal chat mode.
Return only valid JSON. Answer like a helpful conversational assistant without using saved-memory context."""
