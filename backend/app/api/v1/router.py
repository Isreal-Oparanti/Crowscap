from fastapi import APIRouter

from app.api.v1 import captures, health, qwen, search

api_router = APIRouter()
api_router.include_router(captures.router, prefix="/captures")
api_router.include_router(health.router)
api_router.include_router(qwen.router, prefix="/qwen")
api_router.include_router(search.router, prefix="/search")
