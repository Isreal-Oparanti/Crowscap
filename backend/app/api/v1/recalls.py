from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.config import get_settings
from app.core.auth import CurrentUser, require_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.recall import (
    DueRecallsResponse,
    RecallAnswerRequest,
    RecallAnswerResponse,
    RecallQuickRequest,
    RecallQuickResponse,
)
from app.schemas.reminder import ReminderResponse, ReminderSnoozeRequest
from app.services.recall_evaluation_service import (
    RecallEvaluationError,
    RecallEvaluator,
    answer_recall,
    get_recall_evaluator,
    quick_recall,
)
from app.services.recall_service import get_due_recalls
from app.services.reminder_service import complete_reminder, snooze_reminder

router = APIRouter(tags=["recalls"])
logger = get_logger("api.recalls")


@router.get("/due", response_model=DueRecallsResponse)
def due_recalls(
    limit: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> DueRecallsResponse:
    settings = get_settings()
    return get_due_recalls(db=db, limit=limit or settings.recall_due_limit, user_id=current_user.id)


@router.post("/reminders/{reminder_id}/complete", response_model=ReminderResponse)
def complete_due_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ReminderResponse:
    try:
        return complete_reminder(db=db, reminder_id=reminder_id, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reminders/{reminder_id}/snooze", response_model=ReminderResponse)
def snooze_due_reminder(
    reminder_id: str,
    payload: ReminderSnoozeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ReminderResponse:
    try:
        return snooze_reminder(
            db=db,
            reminder_id=reminder_id,
            minutes=payload.minutes,
            user_id=current_user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{memory_id}/answer", response_model=RecallAnswerResponse)
def submit_recall_answer(
    memory_id: str,
    payload: RecallAnswerRequest,
    db: Session = Depends(get_db),
    evaluator: RecallEvaluator = Depends(get_recall_evaluator),
    current_user: CurrentUser = Depends(require_current_user),
) -> RecallAnswerResponse:
    try:
        return answer_recall(
            db=db,
            memory_id=memory_id,
            payload=payload,
            evaluator=evaluator,
            user_id=current_user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (QwenClientError, RecallEvaluationError) as exc:
        logger.warning("\u26a0\ufe0f recall.answer.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{memory_id}/quick", response_model=RecallQuickResponse)
def submit_quick_recall(
    memory_id: str,
    payload: RecallQuickRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> RecallQuickResponse:
    try:
        return quick_recall(db=db, memory_id=memory_id, payload=payload, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
