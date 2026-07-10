from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Capture, Memory, Source
from app.schemas.belief import BeliefAuditRequest, PublicEvidenceResult
from app.services.belief_audit_service import QwenBeliefAuditor
from app.services.public_search_service import PublicSearchError


class FakeAuditClient:
    def chat_json(self, **kwargs):
        assert "final judge of truth" in kwargs["user_prompt"]
        assert "Public source leads" in kwargs["user_prompt"]
        return {
            "answer": (
                "Your saved notes treat distribution as something to test early, but the "
                "public leads suggest checking the evidence for when that sequencing matters."
            ),
            "current_understanding": (
                "The saved memory says founders should test distribution channels early."
            ),
            "strongest_saved_ideas": [
                "Founders should test distribution channels before launch."
            ],
            "public_evidence_summary": (
                "The public source leads add outside context, but snippets alone are not proof."
            ),
            "unsupported_or_weak_points": [
                "The saved note does not cite evidence for every startup category."
            ],
            "ideas_to_compare": [
                "Early channel testing may matter differently before and after product demand exists."
            ],
            "confidence": "medium",
            "confidence_reason": "There is one relevant saved memory and one public source lead.",
            "next_questions": [
                "What product category are you applying this distribution idea to?"
            ],
        }


class FakeEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakePublicSearch:
    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        return [
            PublicEvidenceResult(
                title="Distribution channels overview",
                url=f"https://example.com/{query.replace(' ', '-')}",
                snippet="A public source lead about startup distribution and customer acquisition.",
                source="example.com",
                query=query,
                rank=1,
            )
        ][:limit]


class FailingPublicSearch:
    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        raise PublicSearchError("Search unavailable.")


def build_seeded_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    source = Source(source_type="text", title="Distribution note")
    db.add(source)
    db.flush()
    capture = Capture(source_id=source.id, inferred_intents=["remember"], status="ready")
    db.add(capture)
    db.flush()
    db.add(
        Memory(
            source_id=source.id,
            capture_id=capture.id,
            memory_type="principle",
            epistemic_label="advice",
            content="Founders should test distribution channels before launch.",
            confidence="medium",
            source_strength="moderate",
            embedding_json=[1.0, 0.0],
        )
    )
    db.commit()
    return testing_session


def test_belief_audit_combines_saved_memory_and_public_evidence() -> None:
    testing_session = build_seeded_session()
    db = testing_session()
    auditor = QwenBeliefAuditor(
        client=FakeAuditClient(),
        embedder=FakeEmbedder(),
        public_search=FakePublicSearch(),
    )

    response = auditor.audit(
        db=db,
        payload=BeliefAuditRequest(topic="startup distribution"),
    )

    assert response.topic == "startup distribution"
    assert response.public_search_status == "searched"
    assert len(response.memories) == 1
    assert len(response.public_evidence) == 3
    assert response.confidence == "medium"
    assert "snippets alone are not proof" in response.public_evidence_summary
    db.close()


def test_belief_audit_still_runs_when_public_search_fails() -> None:
    testing_session = build_seeded_session()
    db = testing_session()
    auditor = QwenBeliefAuditor(
        client=FakeAuditClient(),
        embedder=FakeEmbedder(),
        public_search=FailingPublicSearch(),
    )

    response = auditor.audit(
        db=db,
        payload=BeliefAuditRequest(topic="startup distribution", public_query_count=1),
    )

    assert response.public_search_status == "failed"
    assert response.public_search_message == "Search unavailable."
    assert len(response.memories) == 1
    db.close()
