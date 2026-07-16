from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Capture, Memory, Reminder, Source, UserPreference, utc_now
from app.mcp.tools import (
    audit_belief_tool,
    get_due_recalls_tool,
    get_user_preferences_tool,
    search_memory_tool,
)
from app.schemas.belief import BeliefAuditRequest, BeliefAuditResponse, PublicEvidenceResult
from app.schemas.search import SearchResult


class FakeSearchEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        query = texts[0].lower()
        if "distribution" in query or "customer" in query:
            return [[1.0, 0.0, 0.0]]
        return [[0.0, 1.0, 0.0]]


class FakeAuditor:
    def audit(
        self,
        *,
        db: Session,
        payload: BeliefAuditRequest,
        user_id: str | None = None,
    ) -> BeliefAuditResponse:
        return BeliefAuditResponse(
            topic=payload.topic,
            answer="Your saved notes treat distribution as an early learning loop.",
            current_understanding="Distribution is tied to product learning.",
            strongest_saved_ideas=["Test distribution before launch."],
            public_evidence_summary="Public evidence was disabled for this local test.",
            unsupported_or_weak_points=["The exact timing still depends on context."],
            ideas_to_compare=["Product demand may change how early channel testing should start."],
            confidence="medium",
            confidence_reason="There is one relevant saved memory.",
            next_questions=["What would prove this channel is reaching the right users?"],
            memories=[
                SearchResult(
                    memory_id="memory-1",
                    source_id="source-1",
                    source_type="text",
                    source_title="Distribution note",
                    memory_type="principle",
                    epistemic_label="advice",
                    content="Test distribution before launch.",
                    summary=None,
                    confidence="medium",
                    confidence_reason=None,
                    source_strength="moderate",
                    similarity_score=0.9,
                    embedding_dimensions=3,
                )
            ],
            public_evidence=[
                PublicEvidenceResult(
                    title="Source lead",
                    url="https://example.com/distribution",
                    snippet="A source lead about startup distribution.",
                    source="example.com",
                    query="startup distribution",
                    rank=1,
                )
            ],
            public_search_status="searched",
        )


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session


def seed_memory(db: Session) -> Memory:
    source = Source(source_type="text", title="Distribution note")
    db.add(source)
    db.flush()
    capture = Capture(source_id=source.id, inferred_intents=["remember"], status="ready")
    db.add(capture)
    db.flush()
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="principle",
        epistemic_label="advice",
        content="Founders should test distribution channels early.",
        confidence="medium",
        source_strength="moderate",
        embedding_json=[1.0, 0.0, 0.0],
        next_review_at=utc_now() - timedelta(hours=2),
        recall_score=0.58,
    )
    db.add(memory)
    db.commit()
    return memory


def test_mcp_search_memory_returns_compact_semantic_results() -> None:
    testing_session = build_session_factory()
    db = testing_session()
    seed_memory(db)

    payload = search_memory_tool(
        db=db,
        embedder=FakeSearchEmbedder(),
        query="how do I reach customers?",
        min_score=0.5,
    )

    assert payload["returned_count"] == 1
    assert payload["results"][0]["content"] == "Founders should test distribution channels early."
    assert "embedding_dimensions" not in payload["results"][0]
    db.close()


def test_mcp_due_recalls_returns_memories_and_reminders() -> None:
    testing_session = build_session_factory()
    db = testing_session()
    memory = seed_memory(db)
    db.add(
        Reminder(
            content="Apply for the founder program",
            due_at=utc_now() - timedelta(minutes=5),
            save_as_memory=0,
            status="scheduled",
        )
    )
    db.commit()

    payload = get_due_recalls_tool(db=db, limit=5)

    assert payload["due_count"] == 2
    assert payload["memories"][0]["memory_id"] == memory.id
    assert payload["reminders"][0]["content"] == "Apply for the founder program"
    db.close()


def test_mcp_preferences_returns_learned_profile() -> None:
    testing_session = build_session_factory()
    db = testing_session()
    db.add(
        UserPreference(
            profile_key="default",
            answer_style="concise",
            evidence_strictness="strict",
            challenge_style="direct",
            topics_of_interest=["startups", "product"],
            source_preferences={"avoid_weak": ["youtube"]},
        )
    )
    db.commit()

    payload = get_user_preferences_tool(db=db)

    assert payload["answer_style"] == "concise"
    assert payload["evidence_strictness"] == "strict"
    assert payload["topics_of_interest"] == ["startups", "product"]
    db.close()


def test_mcp_audit_belief_returns_agent_ready_summary() -> None:
    testing_session = build_session_factory()
    db = testing_session()

    payload = audit_belief_tool(
        db=db,
        auditor=FakeAuditor(),
        topic="startup distribution",
        include_public_evidence=False,
    )

    assert payload["topic"] == "startup distribution"
    assert payload["memory_count"] == 1
    assert payload["public_evidence_count"] == 1
    assert payload["confidence"] == "medium"
    assert payload["memories"][0]["source_title"] == "Distribution note"
    db.close()
