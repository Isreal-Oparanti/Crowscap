from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.recall import DueRecallsResponse, RecallAnswerRequest, RecallAnswerResponse
from app.services.recall_evaluation_service import (
    RecallEvaluationError,
    RecallEvaluator,
    answer_recall,
    get_recall_evaluator,
)
from app.services.recall_service import get_due_recalls

router = APIRouter(tags=["recalls"])
logger = get_logger("api.recalls")


@router.get("/due", response_model=DueRecallsResponse)
def due_recalls(
    limit: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DueRecallsResponse:
    settings = get_settings()
    return get_due_recalls(db=db, limit=limit or settings.recall_due_limit)


@router.post("/{memory_id}/answer", response_model=RecallAnswerResponse)
def submit_recall_answer(
    memory_id: str,
    payload: RecallAnswerRequest,
    db: Session = Depends(get_db),
    evaluator: RecallEvaluator = Depends(get_recall_evaluator),
) -> RecallAnswerResponse:
    try:
        return answer_recall(
            db=db,
            memory_id=memory_id,
            payload=payload,
            evaluator=evaluator,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (QwenClientError, RecallEvaluationError) as exc:
        logger.warning("\u26a0\ufe0f recall.answer.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
