from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.capture import TextCaptureRequest, TextCaptureResponse
from app.services.capture_service import create_text_capture
from app.services.embedding_service import EmbeddingError, MemoryEmbedder, get_memory_embedder
from app.services.extraction_service import ExtractionError, MemoryExtractor, get_memory_extractor
from app.services.relationship_service import MemoryRelationDetector, get_memory_relation_detector

router = APIRouter(tags=["captures"])
logger = get_logger("api.captures")


@router.post("/text", response_model=TextCaptureResponse)
def capture_text(
    payload: TextCaptureRequest,
    db: Session = Depends(get_db),
    extractor: MemoryExtractor = Depends(get_memory_extractor),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    relation_detector: MemoryRelationDetector = Depends(get_memory_relation_detector),
) -> TextCaptureResponse:
    try:
        return create_text_capture(
            db=db,
            payload=payload,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
        )
    except QwenClientError as exc:
        logger.warning("\u26a0\ufe0f capture.text.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ExtractionError as exc:
        logger.warning("\u26a0\ufe0f capture.text.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingError as exc:
        logger.warning("\u26a0\ufe0f capture.text.embedding_failed reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
