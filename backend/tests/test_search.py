from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Capture, Memory, Source
from app.db.session import get_db
from app.main import app
from app.services.embedding_service import get_memory_embedder


class FakeSearchEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        query = texts[0].lower()
        if "customer" in query or "distribution" in query:
            return [[1.0, 0.0, 0.0]]
        if "cooking" in query or "recipe" in query:
            return [[0.0, 0.0, 1.0]]
        return [[0.0, 1.0, 0.0]]


def build_seeded_db_override():
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
    db.add_all(
        [
            Memory(
                source_id=source.id,
                capture_id=capture.id,
                memory_type="principle",
                epistemic_label="advice",
                content="Founders should test distribution channels early.",
                confidence="medium",
                source_strength="moderate",
                embedding_json=[1.0, 0.0, 0.0],
            ),
            Memory(
                source_id=source.id,
                capture_id=capture.id,
                memory_type="reference",
                epistemic_label="source_summary",
                content="Pricing experiments can reveal how customers perceive value.",
                confidence="medium",
                source_strength="moderate",
                embedding_json=[0.0, 1.0, 0.0],
            ),
        ]
    )
    db.commit()
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    return override_db


def test_search_returns_semantic_match_above_threshold() -> None:
    app.dependency_overrides[get_db] = build_seeded_db_override()
    app.dependency_overrides[get_memory_embedder] = lambda: FakeSearchEmbedder()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={
                "query": "how do I get my product to customers",
                "min_score": 0.65,
                "limit": 10,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["candidate_count"] == 2
        assert payload["embedded_candidate_count"] == 2
        assert payload["returned_count"] == 1
        assert payload["top_score"] == 1.0
        assert len(payload["results"]) == 1
        assert payload["results"][0]["content"] == "Founders should test distribution channels early."
        assert payload["results"][0]["source_title"] == "Distribution note"
        assert payload["results"][0]["similarity_score"] == 1.0
    finally:
        app.dependency_overrides.clear()


def test_search_can_return_no_results_when_below_threshold() -> None:
    app.dependency_overrides[get_db] = build_seeded_db_override()
    app.dependency_overrides[get_memory_embedder] = lambda: FakeSearchEmbedder()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={
                "query": "cooking recipes",
                "min_score": 0.65,
                "limit": 10,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["candidate_count"] == 2
        assert payload["embedded_candidate_count"] == 2
        assert payload["returned_count"] == 0
        assert payload["top_score"] == 0.0
        assert payload["results"] == []
    finally:
        app.dependency_overrides.clear()
