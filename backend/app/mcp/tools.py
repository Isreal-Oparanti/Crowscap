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
from app.schemas.capture import TextCaptureRequest
from app.schemas.memory import ArchiveMemoryRequest
from app.schemas.recall import RecallQuickRequest
from app.schemas.search import SearchRequest
from app.services.belief_audit_service import BeliefAuditor, QwenBeliefAuditor
from app.services.capture_service import create_text_capture
from app.services.embedding_service import MemoryEmbedder, QwenMemoryEmbedder
from app.services.extraction_service import MemoryExtractor, QwenMemoryExtractor
from app.services.memory_lifecycle_service import archive_memory
from app.services.preference_service import get_or_create_user_preferences, preference_response
from app.services.recall_evaluation_service import quick_recall
from app.services.recall_service import get_due_recalls
from app.services.relationship_service import MemoryRelationDetector, QwenMemoryRelationDetector
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


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------


def capture_text_tool(
    *,
    content: str,
    user_note: str | None = None,
    intent_text: str | None = None,
    source_title: str | None = None,
    user_id: str | None = None,
    db: Session | None = None,
    extractor: MemoryExtractor | None = None,
    embedder: MemoryEmbedder | None = None,
    relation_detector: MemoryRelationDetector | None = None,
) -> dict[str, Any]:
    """Save text as memory atoms via the full Crowscap extraction pipeline."""
    with _session_scope(db) as session:
        response = create_text_capture(
            db=session,
            payload=TextCaptureRequest(
                content=content,
                user_note=user_note,
                intent_text=intent_text,
                source_title=source_title,
            ),
            extractor=extractor or QwenMemoryExtractor(),
            embedder=embedder or QwenMemoryEmbedder(),
            relation_detector=relation_detector or QwenMemoryRelationDetector(),
            user_id=user_id,
        )

    return {
        "capture_id": response.capture_id,
        "source_id": response.source_id,
        "source_type": response.source_type,
        "source_title": response.source_title,
        "status": response.status,
        "inferred_intents": list(response.inferred_intents),
        "memory_count": len(response.memories),
        "memories": [
            {
                "id": memory.id,
                "memory_type": memory.memory_type,
                "epistemic_label": memory.epistemic_label,
                "content": memory.content,
                "summary": memory.summary,
                "confidence": memory.confidence,
                "source_strength": memory.source_strength,
            }
            for memory in response.memories
        ],
    }


def quick_recall_tool(
    *,
    memory_id: str,
    action: str,
    user_id: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Submit a quick recall signal for a due memory without a Qwen evaluation round-trip."""
    with _session_scope(db) as session:
        response = quick_recall(
            db=session,
            memory_id=memory_id,
            payload=RecallQuickRequest(action=action),  # type: ignore[arg-type]
            user_id=user_id,
        )

    return {
        "memory_id": response.memory_id,
        "action": response.action,
        "feedback": response.feedback,
        "next_due_at": response.next_due_at.isoformat(),
        "review_count": response.review_count,
        "recall_score": response.recall_score,
    }


def archive_memory_tool(
    *,
    memory_id: str,
    reason: str = "user_dismissed",
    note: str | None = None,
    user_id: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Archive a memory so it stops surfacing in recalls and searches."""
    with _session_scope(db) as session:
        response = archive_memory(
            db=session,
            memory_id=memory_id,
            payload=ArchiveMemoryRequest(reason=reason, note=note),  # type: ignore[arg-type]
            user_id=user_id,
        )

    return {
        "memory_id": response.memory_id,
        "previous_status": response.previous_status,
        "new_status": response.new_status,
        "reason": response.reason,
        "note": response.note,
        "archived_at": response.archived_at.isoformat(),
    }
