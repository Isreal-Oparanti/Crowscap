from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.logging import get_logger
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

router = APIRouter(tags=["chat"])
logger = get_logger("api.chat")


@router.get("/conversations/current", response_model=ConversationResponse | None)
def current_conversation(db: Session = Depends(get_db)) -> ConversationResponse | None:
    return get_current_conversation(db=db)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationResponse:
    found = get_conversation(db=db, conversation_id=conversation_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return found


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    router_service: ChatIntentRouter = Depends(get_chat_router),
    synthesizer: ChatSynthesizer = Depends(get_chat_synthesizer),
    conversation_responder: ChatConversationResponder = Depends(get_chat_conversation_responder),
    belief_auditor: BeliefAuditor = Depends(get_belief_auditor),
    extractor: MemoryExtractor = Depends(get_memory_extractor),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    relation_detector: MemoryRelationDetector = Depends(get_memory_relation_detector),
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
    ) as exc:
        logger.warning("\u26a0\ufe0f chat.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
        )
    except (QwenClientError, EmbeddingError) as exc:
        logger.warning("\u26a0\ufe0f chat.pdf.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ChatSynthesisError, ExtractionError, IngestionError) as exc:
        logger.warning("\u26a0\ufe0f chat.pdf.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
