from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.auth import CurrentUser, require_current_user
from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, PaginatedMessagesResponse
from app.services.belief_audit_service import BeliefAuditError, BeliefAuditor, get_belief_auditor
from app.services.chat_service import (
    ChatIntentRouter,
    ChatRoutingError,
    ChatSynthesisError,
    ChatSynthesizer,
    ChatConversationResponder,
    create_new_conversation,
    delete_conversation_by_id,
    get_chat_conversation_responder,
    get_conversation,
    get_current_conversation,
    get_paginated_chat_messages,
    get_chat_router,
    get_chat_synthesizer,
    list_user_conversations,
    process_chat_pdf_upload,
    process_chat_message,
)
from app.services.embedding_service import EmbeddingError, MemoryEmbedder, get_memory_embedder
from app.services.extraction_service import ExtractionError, MemoryExtractor, get_memory_extractor
from app.services.ingestion_service import IngestionError
from app.services.relationship_service import MemoryRelationDetector, get_memory_relation_detector
from app.services.safety_service import CaptureSafetyError

router = APIRouter(tags=["chat"])
logger = get_logger("api.chat")

REASONING_UNAVAILABLE_MESSAGE = (
    "Crowscap could not reach its reasoning engine right now. Please try again in a moment."
)


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[ConversationResponse]:
    return list_user_conversations(db=db, user_id=current_user.id, limit=limit)


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ConversationResponse:
    return create_new_conversation(db=db, user_id=current_user.id)


@router.get("/conversations/current", response_model=ConversationResponse | None)
def current_conversation(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ConversationResponse | None:
    return get_current_conversation(db=db, user_id=current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ConversationResponse:
    found = get_conversation(db=db, conversation_id=conversation_id, user_id=current_user.id)
    if found is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return found


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> Response:
    ok = delete_conversation_by_id(db=db, conversation_id=conversation_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return Response(status_code=204)


@router.get("/messages", response_model=PaginatedMessagesResponse)
def paginated_messages(
    limit: int = Query(default=20, ge=1, le=100),
    before_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> PaginatedMessagesResponse:
    return get_paginated_chat_messages(
        db=db,
        user_id=current_user.id,
        limit=limit,
        before_id=before_id,
    )


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    router_service: ChatIntentRouter = Depends(get_chat_router),
    synthesizer: ChatSynthesizer = Depends(get_chat_synthesizer),
    conversation_responder: ChatConversationResponder = Depends(get_chat_conversation_responder),
    belief_auditor: BeliefAuditor = Depends(get_belief_auditor),
    extractor: MemoryExtractor = Depends(get_memory_extractor),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    relation_detector: MemoryRelationDetector = Depends(get_memory_relation_detector),
    current_user: CurrentUser = Depends(require_current_user),
    _: None = Depends(rate_limit("chat", limit=30)),
) -> ChatResponse:
    try:
        return process_chat_message(
            db=db,
            payload=payload,
            router=router_service,
            synthesizer=synthesizer,
            conversation_responder=conversation_responder,
            belief_auditor=belief_auditor,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            background_tasks=background_tasks,
            user_id=current_user.id,
        )
    except (QwenClientError, EmbeddingError) as exc:
        logger.warning("⚠️ chat.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=REASONING_UNAVAILABLE_MESSAGE) from exc
    except (
        BeliefAuditError,
        ChatRoutingError,
        ChatSynthesisError,
        ExtractionError,
        IngestionError,
        CaptureSafetyError,
    ) as exc:
        logger.warning("⚠️ chat.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValidationError as exc:
        logger.warning("⚠️ chat.validation_failed reason=%s", exc)
        raise HTTPException(
            status_code=422,
            detail=(
                "I could not turn that into a valid Crowscap action. "
                "Paste the content or link again, or say exactly what you want saved."
            ),
        ) from exc


@router.post("/pdf", response_model=ChatResponse)
async def chat_pdf(
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    intent_text: str | None = Form(default=None),
    user_note: str | None = Form(default=None),
    db: Session = Depends(get_db),
    extractor: MemoryExtractor = Depends(get_memory_extractor),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    relation_detector: MemoryRelationDetector = Depends(get_memory_relation_detector),
    current_user: CurrentUser = Depends(require_current_user),
    _: None = Depends(rate_limit("chat", limit=30)),
) -> ChatResponse:
    try:
        file_bytes = await file.read()
        return process_chat_pdf_upload(
            db=db,
            file_bytes=file_bytes,
            filename=file.filename or "uploaded.pdf",
            conversation_id=conversation_id,
            intent_text=intent_text,
            user_note=user_note,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=current_user.id,
        )
    except (QwenClientError, EmbeddingError) as exc:
        logger.warning("⚠️ chat.pdf.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=REASONING_UNAVAILABLE_MESSAGE) from exc
    except (
        ChatSynthesisError,
        ExtractionError,
        IngestionError,
        CaptureSafetyError,
        ValidationError,
    ) as exc:
        logger.warning("⚠️ chat.pdf.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
