from pydantic import BaseModel
from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import check_database

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    database: str
    qwen_configured: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    database_ok = check_database()

    return HealthResponse(
        status="ok" if database_ok else "degraded",
        app_name=settings.app_name,
        environment=settings.app_env,
        database="ok" if database_ok else "unavailable",
        qwen_configured=settings.has_qwen_key,
    )

