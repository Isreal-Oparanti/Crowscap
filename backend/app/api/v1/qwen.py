from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.ai.qwen_client import QwenClient, QwenClientError
from app.core.config import get_settings

router = APIRouter(tags=["qwen"])


class QwenStatusResponse(BaseModel):
    configured: bool
    base_url: str
    reasoning_model: str
    fast_model: str
    embedding_model: str
    rerank_model: str


class QwenSmokeRequest(BaseModel):
    prompt: str = "Reply with one short sentence confirming Crowscap can reach Qwen Cloud."


class QwenSmokeResponse(BaseModel):
    model: str
    content: str


@router.get("/status", response_model=QwenStatusResponse)
def qwen_status() -> QwenStatusResponse:
    settings = get_settings()
    return QwenStatusResponse(
        configured=settings.has_qwen_key,
        base_url=settings.qwen_base_url,
        reasoning_model=settings.qwen_reasoning_model,
        fast_model=settings.qwen_fast_model,
        embedding_model=settings.qwen_embedding_model,
        rerank_model=settings.qwen_rerank_model,
    )


@router.post("/smoke", response_model=QwenSmokeResponse)
def qwen_smoke(payload: QwenSmokeRequest) -> QwenSmokeResponse:
    client = QwenClient()
    try:
        content = client.chat_once(payload.prompt)
    except QwenClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    settings = get_settings()
    return QwenSmokeResponse(model=settings.qwen_fast_model, content=content)

