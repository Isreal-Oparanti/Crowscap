from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import socket

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.config import mask_url_credentials
from app.core.logging import configure_logging, get_logger
from app.db.schema import ensure_database_schema
from app.db.session import check_database
from app.db.session import engine

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
    safe_database_url = mask_url_credentials(settings.database_url)
    if database_ok:
        ensure_database_schema(engine=engine, database_url=settings.database_url)
        logger.info("\U0001f5c4\ufe0f db.connected status=ok url=%s", safe_database_url)
    else:
        logger.error("\u274c db.connected status=failed url=%s", safe_database_url)

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

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception(
            "\u274c app.database_error path=%s error_type=%s",
            request.url.path,
            type(exc).__name__,
        )
        if _looks_like_connectivity_error(exc):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "Crowscap could not reach the memory database right now. "
                        "This looks like a temporary network issue. Please check your connection and try again."
                    ),
                    "error_code": "database_unavailable",
                    "retryable": True,
                },
            )
        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    "Crowscap hit a database error while saving or reading memory. "
                    "Please try again, and if it repeats, the memory service needs attention."
                ),
                "error_code": "database_error",
                "retryable": False,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "\u274c app.unhandled_error path=%s error_type=%s",
            request.url.path,
            type(exc).__name__,
        )
        if _looks_like_connectivity_error(exc):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "Crowscap could not reach one of its services right now. "
                        "Please check your internet connection and try again."
                    ),
                    "error_code": "service_unavailable",
                    "retryable": True,
                },
            )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Crowscap hit an unexpected internal error. Please try again.",
                "error_code": "internal_error",
                "retryable": False,
            },
        )

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "status": "ok",
            "docs": "/docs",
        }

    return app


def _looks_like_connectivity_error(exc: Exception) -> bool:
    if isinstance(exc, (ConnectionError, TimeoutError, socket.gaierror)):
        return True

    parts: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(f"{type(current).__name__}: {current}")
        current = current.__cause__ or current.__context__

    text = " ".join(parts).lower()
    return any(
        marker in text
        for marker in (
            "getaddrinfo failed",
            "failed to resolve host",
            "could not translate host name",
            "temporary failure in name resolution",
            "name or service not known",
            "connection refused",
            "connection reset",
            "network is unreachable",
            "timed out",
            "timeout",
        )
    )


app = create_app()
