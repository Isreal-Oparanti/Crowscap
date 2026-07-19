from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.auth import CurrentUser, require_current_user
from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.embedding_service import EmbeddingError, MemoryEmbedder, get_memory_embedder
from app.services.search_service import search_memories

router = APIRouter(tags=["search"])
logger = get_logger("api.search")


@router.post("", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    embedder: MemoryEmbedder = Depends(get_memory_embedder),
    current_user: CurrentUser = Depends(require_current_user),
    _: None = Depends(rate_limit("search", limit=60)),
) -> SearchResponse:
    try:
        return search_memories(db=db, payload=payload, embedder=embedder, user_id=current_user.id)
    except (QwenClientError, EmbeddingError) as exc:
        logger.warning("\u26a0\ufe0f search.unavailable reason=%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
