from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.auth import CurrentUser, require_current_user
from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.capture import TextCaptureRequest, TextCaptureResponse, UrlCaptureRequest
from app.services.capture_service import create_text_capture
from app.services.embedding_service import EmbeddingError, MemoryEmbedder, get_memory_embedder
from app.services.extraction_service import ExtractionError, MemoryExtractor, get_memory_extractor
from app.services.ingestion_service import (
    IngestionError,
    create_pdf_capture_from_bytes,
    create_url_capture,
)
from app.services.relationship_service import MemoryRelationDetector, get_memory_relation_detector
from app.services.safety_service import CaptureSafetyError

router = APIRouter(tags=["captures"])
logger = get_logger("api.captures")


@router.post("/text", response_model=TextCaptureResponse)
def capture_text(
    payload: TextCaptureRequest,
    db: Session = Depends(get_db),
    extractor: MemoryExtractor = Depends(get_memory_extractor),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    relation_detector: MemoryRelationDetector = Depends(get_memory_relation_detector),
    current_user: CurrentUser = Depends(require_current_user),
    _: None = Depends(rate_limit("captures", limit=20)),
) -> TextCaptureResponse:
    try:
        return create_text_capture(
            db=db,
            payload=payload,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=current_user.id,
        )
    except QwenClientError as exc:
        logger.warning("\u26a0\ufe0f capture.text.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ExtractionError, CaptureSafetyError) as exc:
        logger.warning("\u26a0\ufe0f capture.text.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingError as exc:
        logger.warning("\u26a0\ufe0f capture.text.embedding_failed reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/url", response_model=TextCaptureResponse)
def capture_url(
    payload: UrlCaptureRequest,
    db: Session = Depends(get_db),
    extractor: MemoryExtractor = Depends(get_memory_extractor),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    relation_detector: MemoryRelationDetector = Depends(get_memory_relation_detector),
    current_user: CurrentUser = Depends(require_current_user),
    _: None = Depends(rate_limit("captures", limit=20)),
) -> TextCaptureResponse:
    try:
        return create_url_capture(
            db=db,
            payload=payload,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=current_user.id,
        )
    except QwenClientError as exc:
        logger.warning("\u26a0\ufe0f capture.url.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ExtractionError, IngestionError, CaptureSafetyError) as exc:
        logger.warning("\u26a0\ufe0f capture.url.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingError as exc:
        logger.warning("\u26a0\ufe0f capture.url.embedding_failed reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/pdf", response_model=TextCaptureResponse)
async def capture_pdf(
    file: UploadFile = File(...),
    intent_text: str | None = Form(default=None),
    user_note: str | None = Form(default=None),
    db: Session = Depends(get_db),
    extractor: MemoryExtractor = Depends(get_memory_extractor),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    relation_detector: MemoryRelationDetector = Depends(get_memory_relation_detector),
    current_user: CurrentUser = Depends(require_current_user),
    _: None = Depends(rate_limit("captures", limit=20)),
) -> TextCaptureResponse:
    try:
        file_bytes = await file.read()
        return create_pdf_capture_from_bytes(
            db=db,
            file_bytes=file_bytes,
            filename=file.filename or "uploaded.pdf",
            intent_text=intent_text,
            user_note=user_note,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=current_user.id,
        )
    except QwenClientError as exc:
        logger.warning("\u26a0\ufe0f capture.pdf.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ExtractionError, IngestionError, CaptureSafetyError) as exc:
        logger.warning("\u26a0\ufe0f capture.pdf.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingError as exc:
        logger.warning("\u26a0\ufe0f capture.pdf.embedding_failed reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
