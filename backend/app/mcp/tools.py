from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.mcp.formatters import (
    compact_due_memory,
    compact_reminder,
    compact_search_result,
    dump_model,
)
from app.schemas.belief import BeliefAuditRequest
from app.schemas.search import SearchRequest
from app.services.belief_audit_service import BeliefAuditor, QwenBeliefAuditor
from app.services.embedding_service import MemoryEmbedder, QwenMemoryEmbedder
from app.services.preference_service import get_or_create_user_preferences, preference_response
from app.services.recall_service import get_due_recalls
from app.services.search_service import search_memories


@contextmanager
def _session_scope(db: Session | None = None) -> Iterator[Session]:
    if db is not None:
        yield db
        return

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def search_memory_tool(
    *,
    query: str,
    limit: int = 5,
    min_score: float = 0.25,
    include_archived: bool = False,
    user_id: str | None = None,
    db: Session | None = None,
    embedder: MemoryEmbedder | None = None,
) -> dict[str, Any]:
    with _session_scope(db) as session:
        response = search_memories(
            db=session,
            payload=SearchRequest(
                query=query,
                limit=limit,
                min_score=min_score,
                include_archived=include_archived,
            ),
            embedder=embedder or QwenMemoryEmbedder(),
            user_id=user_id,
        )

    return {
        "query": response.query,
        "min_score": response.min_score,
        "candidate_count": response.candidate_count,
        "embedded_candidate_count": response.embedded_candidate_count,
        "returned_count": response.returned_count,
        "top_score": response.top_score,
        "results": [compact_search_result(result) for result in response.results],
    }


def audit_belief_tool(
    *,
    topic: str,
    include_public_evidence: bool = True,
    memory_limit: int = 8,
    public_query_count: int = 3,
    public_results_per_query: int = 3,
    user_id: str | None = None,
    db: Session | None = None,
    auditor: BeliefAuditor | None = None,
) -> dict[str, Any]:
    with _session_scope(db) as session:
        response = (auditor or QwenBeliefAuditor()).audit(
            db=session,
            payload=BeliefAuditRequest(
                topic=topic,
                include_public_evidence=include_public_evidence,
                memory_limit=memory_limit,
                public_query_count=public_query_count,
                public_results_per_query=public_results_per_query,
            ),
            user_id=user_id,
        )

    return {
        "topic": response.topic,
        "answer": response.answer,
        "current_understanding": response.current_understanding,
        "strongest_saved_ideas": response.strongest_saved_ideas,
        "public_evidence_summary": response.public_evidence_summary,
        "unsupported_or_weak_points": response.unsupported_or_weak_points,
        "ideas_to_compare": response.ideas_to_compare,
        "confidence": response.confidence,
        "confidence_reason": response.confidence_reason,
        "next_questions": response.next_questions,
        "memory_count": len(response.memories),
        "public_evidence_count": len(response.public_evidence),
        "public_search_status": response.public_search_status,
        "public_search_message": response.public_search_message,
        "memories": [compact_search_result(memory) for memory in response.memories],
        "public_evidence": [dump_model(evidence) for evidence in response.public_evidence],
    }


def get_due_recalls_tool(
    *,
    limit: int = 5,
    user_id: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    with _session_scope(db) as session:
        response = get_due_recalls(db=session, limit=limit, user_id=user_id)

    return {
        "due_count": response.due_count,
        "now": response.now.isoformat(),
        "memories": [compact_due_memory(memory) for memory in response.memories],
        "reminders": [compact_reminder(reminder) for reminder in response.reminders],
    }


def get_user_preferences_tool(
    *,
    user_id: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    with _session_scope(db) as session:
        profile = get_or_create_user_preferences(db=session, user_id=user_id)
        response = preference_response(profile)

    return dump_model(response)
