from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.belief import BeliefAuditRequest, BeliefAuditResponse
from app.services.belief_audit_service import (
    BeliefAuditError,
    BeliefAuditor,
    get_belief_auditor,
)
from app.services.embedding_service import EmbeddingError

router = APIRouter(tags=["beliefs"])
logger = get_logger("api.beliefs")


@router.post("/audit", response_model=BeliefAuditResponse)
def audit_belief(
    payload: BeliefAuditRequest,
    db: Session = Depends(get_db),
    auditor: BeliefAuditor = Depends(get_belief_auditor),
) -> BeliefAuditResponse:
    try:
        return auditor.audit(db=db, payload=payload)
    except (QwenClientError, EmbeddingError) as exc:
        logger.warning("⚠️ belief.audit.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BeliefAuditError as exc:
        logger.warning("⚠️ belief.audit.invalid reason=%s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
