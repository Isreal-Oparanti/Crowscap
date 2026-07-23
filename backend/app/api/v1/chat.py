from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.auth import CurrentUser, require_current_user
from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.belief_audit_service import BeliefAuditError, BeliefAuditor, get_belief_auditor
from app.services.chat_service import (
    ChatIntentRouter,
    ChatRoutingError,
    ChatSynthesisError,
    ChatSynthesizer,
    ChatConversationResponder,
    get_chat_conversation_responder,
    get_conversation,
    get_current_conversation,
    get_chat_router,
    get_chat_synthesizer,
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
        logger.warning("\u26a0\ufe0f chat.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (
        BeliefAuditError,
        ChatRoutingError,
        ChatSynthesisError,
        ExtractionError,
        IngestionError,
        CaptureSafetyError,
    ) as exc:
        logger.warning("\u26a0\ufe0f chat.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValidationError as exc:
        logger.warning("\u26a0\ufe0f chat.validation_failed reason=%s", exc)
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
        logger.warning("\u26a0\ufe0f chat.pdf.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (
        ChatSynthesisError,
        ExtractionError,
        IngestionError,
        CaptureSafetyError,
        ValidationError,
    ) as exc:
        logger.warning("\u26a0\ufe0f chat.pdf.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
