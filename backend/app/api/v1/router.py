from fastapi import APIRouter

from app.api.v1 import (
    actions,
    beliefs,
    captures,
    chat,
    health,
    jobs,
    memories,
    preferences,
    qwen,
    recalls,
    search,
    sources,
    admin,
)

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin")
api_router.include_router(chat.router, prefix="/chat")
api_router.include_router(actions.router, prefix="/actions")
api_router.include_router(beliefs.router, prefix="/beliefs")
api_router.include_router(captures.router, prefix="/captures")
api_router.include_router(health.router)
api_router.include_router(jobs.router, prefix="/jobs")
api_router.include_router(memories.router, prefix="/memories")
api_router.include_router(preferences.router, prefix="/preferences")
api_router.include_router(qwen.router, prefix="/qwen")
api_router.include_router(recalls.router, prefix="/recalls")
api_router.include_router(search.router, prefix="/search")
api_router.include_router(sources.router, prefix="/sources")
