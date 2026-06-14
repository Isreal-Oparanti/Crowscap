from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import check_database

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()

    logger.info(
        "\U0001f680 app.start name=%s env=%s api_prefix=%s",
        settings.app_name,
        settings.app_env,
        settings.api_v1_prefix,
    )
    logger.info(
        "\U0001f9e0 qwen.configured status=%s base_url=%s fast_model=%s",
        settings.has_qwen_key,
        settings.qwen_base_url,
        settings.qwen_fast_model,
    )

    database_ok = check_database()
    if database_ok:
        logger.info("\U0001f5c4\ufe0f db.connected status=ok url=%s", settings.database_url)
    else:
        logger.error("\u274c db.connected status=failed url=%s", settings.database_url)

    yield

    logger.info("\U0001f44b app.shutdown name=%s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "status": "ok",
            "docs": "/docs",
        }

    return app


app = create_app()
