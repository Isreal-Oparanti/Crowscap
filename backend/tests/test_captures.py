from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.qwen_client import QwenClientError
from app.ai.structured_outputs import CaptureExtraction, ExtractedMemoryAtom
from app.core.auth import CurrentUser, require_current_user
from app.db.base import Base
from app.db.models import Capture, Memory, MemoryRelation, Source  # noqa: F401
from app.db.session import get_db
from app.main import app
from app.services.embedding_service import get_memory_embedder
from app.services.extraction_service import get_memory_extractor
from app.services.relationship_service import get_memory_relation_detector


class FakeExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract_text(
        self,
        *,
        text: str,
        intent_text: str | None = None,
        user_note: str | None = None,
    ) -> CaptureExtraction:
        self.calls += 1
        return CaptureExtraction(
            source_title="Distribution note",
            inferred_intents=["remember", "apply"],
            memories=[
                ExtractedMemoryAtom(
                    memory_type="principle",
                    epistemic_label="advice",
                    content="Early startup teams should test distribution before treating it as a later marketing task.",
                    summary="Distribution should be tested early.",
                    confidence="medium",
                    confidence_reason="The captured text presents this as advice, not measured data.",
                    source_strength="moderate",
                )
            ],
        )


class FailingExtractor:
    def extract_text(
        self,
        *,
        text: str,
        intent_text: str | None = None,
        user_note: str | None = None,
    ) -> CaptureExtraction:
        raise QwenClientError("Could not reach Qwen Cloud. Check internet/DNS.")


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeRelationDetector:
    def __init__(self, *, create_tension: bool = False) -> None:
        self.calls = 0
        self.create_tension = create_tension

    def detect_for_memories(
        self,
        *,
        db: Session,
        new_memories: list[Memory],
        user_id: str | None = None,
    ) -> list[MemoryRelation]:
        self.calls += 1
        if not self.create_tension or not new_memories:
            return []

        older_memory = db.scalars(
            select(Memory)
            .where(Memory.capture_id != new_memories[0].capture_id)
            .where(Memory.user_id.is_(None) if user_id is None else Memory.user_id == user_id)
        ).first()
        if older_memory is None:
            return []

        relation = MemoryRelation(
            source_memory_id=new_memories[0].id,
            target_memory_id=older_memory.id,
            relation_type="tension",
            strength="moderate",
            explanation="The newer idea pulls against the older distribution advice depending on product quality.",
            created_by="test",
        )
        db.add(relation)
        db.flush()
        return [relation]


def build_test_db_override():
    app.dependency_overrides[require_current_user] = lambda: CurrentUser(
        id="test-user",
        email="test@example.com",
        name="Test User",
    )
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    return override_db


def test_capture_text_persists_memory_atoms() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    relation_detector = FakeRelationDetector()
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: relation_detector

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/captures/text",
            json={
                "content": "A founder should not wait until launch to think about distribution. They should test channels early and learn which path reaches customers.",
                "intent_text": "remember and apply this to my startup",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["source_title"] == "Distribution note"
        assert payload["original_content"].startswith("A founder should not wait")
        assert payload["inferred_intents"] == ["remember", "apply"]
        assert len(payload["memories"]) == 1
        assert payload["memories"][0]["memory_type"] == "principle"
        assert payload["memories"][0]["confidence"] == "medium"
        assert payload["memories"][0]["embedding_dimensions"] == 3
        assert payload["memories"][0]["relationships"] == []
        assert extractor.calls == 1
        assert embedder.calls == 1
        assert relation_detector.calls == 1
    finally:
        app.dependency_overrides.clear()


def test_capture_text_returns_503_when_qwen_is_unreachable() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    app.dependency_overrides[get_memory_extractor] = lambda: FailingExtractor()
    embedder = FakeEmbedder()
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: FakeRelationDetector()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/captures/text",
            json={
                "content": "A founder should not wait until launch to think about distribution. They should test channels early and learn which path reaches customers.",
                "intent_text": "remember this",
            },
        )

        assert response.status_code == 503
        assert "Could not reach Qwen Cloud" in response.json()["detail"]
        assert embedder.calls == 0
    finally:
        app.dependency_overrides.clear()


def test_capture_text_rejects_password_like_secret_before_extraction() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    relation_detector = FakeRelationDetector()
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: relation_detector

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/captures/text",
            json={
                "content": (
                    "This note contains a deployment credential that should not be stored. "
                    "api_key = sk_test_1234567890abcdef"
                )
            },
        )

        assert response.status_code == 422
        assert "API keys" in response.json()["detail"]
        assert extractor.calls == 0
        assert embedder.calls == 0
        assert relation_detector.calls == 0
    finally:
        app.dependency_overrides.clear()


def test_capture_text_masks_contact_details_before_storage() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    relation_detector = FakeRelationDetector()
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: relation_detector

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/captures/text",
            json={
                "content": (
                    "A founder wants to follow up with the beta user at ada@example.com "
                    "and +1 415 555 0199 after the onboarding interview."
                )
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert "[email]" in payload["original_content"]
        assert "[phone number]" in payload["original_content"]
        assert "ada@example.com" not in payload["original_content"]
        assert extractor.calls == 1
    finally:
        app.dependency_overrides.clear()


def test_capture_text_reuses_duplicate_text_without_calling_extractor_twice() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    relation_detector = FakeRelationDetector()
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: relation_detector

    request_body = {
        "content": "A founder should not wait until launch to think about distribution. They should test channels early and learn which path reaches customers.",
        "intent_text": "remember and apply this to my startup",
    }

    try:
        client = TestClient(app)
        first_response = client.post("/api/v1/captures/text", json=request_body)
        second_response = client.post("/api/v1/captures/text", json=request_body)

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert extractor.calls == 1
        assert second_response.json()["source_id"] == first_response.json()["source_id"]
        assert second_response.json()["original_content"] == request_body["content"]
        assert second_response.json()["memories"][0]["id"] == first_response.json()["memories"][0]["id"]
        assert second_response.json()["memories"][0]["embedding_dimensions"] == 3
        assert embedder.calls == 1
        assert relation_detector.calls == 1
    finally:
        app.dependency_overrides.clear()


def test_source_endpoint_returns_exact_original_capture() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    app.dependency_overrides[get_memory_extractor] = lambda: FakeExtractor()
    app.dependency_overrides[get_memory_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_memory_relation_detector] = lambda: FakeRelationDetector()
    original = (
        "Line one is preserved exactly.\n\n"
        "Line two keeps its spacing and punctuation: copy trading != AI matching."
    )

    try:
        client = TestClient(app)
        capture_response = client.post(
            "/api/v1/captures/text",
            json={"content": original, "source_title": "Exact source"},
        )
        assert capture_response.status_code == 200

        response = client.get(
            f"/api/v1/sources/{capture_response.json()['source_id']}"
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Exact source"
        assert response.json()["original_content"] == original
    finally:
        app.dependency_overrides.clear()


def test_capture_text_backfills_embeddings_for_existing_duplicate_memories() -> None:
    override_db = build_test_db_override()
    app.dependency_overrides[get_db] = override_db
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    relation_detector = FakeRelationDetector()
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: relation_detector

    content = (
        "A founder should not wait until launch to think about distribution. "
        "They should test channels early and learn which path reaches customers."
    )

    try:
        client = TestClient(app)
        first_response = client.post(
            "/api/v1/captures/text",
            json={
                "content": content,
                "intent_text": "remember and apply this to my startup",
            },
        )
        assert first_response.status_code == 200

        # Simulate older memories created before embeddings existed.
        db = next(override_db())
        memory = db.get(Memory, first_response.json()["memories"][0]["id"])
        assert memory is not None
        memory.embedding_json = None
        db.commit()
        db.close()

        second_response = client.post(
            "/api/v1/captures/text",
            json={
                "content": content,
                "intent_text": "remember and apply this to my startup",
            },
        )

        assert second_response.status_code == 200
        assert extractor.calls == 1
        assert embedder.calls == 2
        assert relation_detector.calls == 1
        assert second_response.json()["memories"][0]["embedding_dimensions"] == 3
    finally:
        app.dependency_overrides.clear()


def test_capture_text_rejects_over_large_text_before_extraction() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: FakeRelationDetector()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/captures/text",
            json={
                "content": "x" * 10_001,
                "intent_text": "remember this",
            },
        )

        assert response.status_code == 422
        assert extractor.calls == 0
        assert embedder.calls == 0
    finally:
        app.dependency_overrides.clear()


def test_capture_text_returns_relationships_from_detector() -> None:
    app.dependency_overrides[get_db] = build_test_db_override()
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    relation_detector = FakeRelationDetector(create_tension=True)
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: relation_detector

    try:
        client = TestClient(app)
        first_response = client.post(
            "/api/v1/captures/text",
            json={
                "content": "A founder should not wait until launch to think about distribution. They should test channels early and learn which path reaches customers.",
                "intent_text": "remember this",
            },
        )
        second_response = client.post(
            "/api/v1/captures/text",
            json={
                "content": "A strong product can create word of mouth, and distribution cannot save something customers do not actually want.",
                "intent_text": "compare this with distribution advice",
            },
        )

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        relationship = second_response.json()["memories"][0]["relationships"][0]
        assert relationship["relationship_type"] == "tension"
        assert relationship["strength"] == "moderate"
        assert relationship["related_memory_id"] == first_response.json()["memories"][0]["id"]
        assert "product quality" in relationship["explanation"]
        assert relation_detector.calls == 2
    finally:
        app.dependency_overrides.clear()


def test_duplicate_capture_backfills_relationships_when_source_was_not_scanned() -> None:
    override_db = build_test_db_override()
    app.dependency_overrides[get_db] = override_db
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    relation_detector = FakeRelationDetector()
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_memory_relation_detector] = lambda: relation_detector

    distribution_body = {
        "content": "A founder should not wait until launch to think about distribution. They should test channels early and learn which path reaches customers.",
        "intent_text": "remember this",
    }
    product_body = {
        "content": "A strong product can create word of mouth, and distribution cannot save something customers do not actually want.",
        "intent_text": "compare this with distribution advice",
    }

    try:
        client = TestClient(app)
        distribution_response = client.post("/api/v1/captures/text", json=distribution_body)
        product_response = client.post("/api/v1/captures/text", json=product_body)

        assert distribution_response.status_code == 200
        assert product_response.status_code == 200
        assert product_response.json()["memories"][0]["relationships"] == []

        # Simulate an older development capture created before relationship scans existed.
        db = next(override_db())
        source = db.get(Source, product_response.json()["source_id"])
        assert source is not None
        source.metadata_json = {"input_kind": "text_capture"}
        db.commit()
        db.close()

        relation_detector.create_tension = True
        duplicate_response = client.post("/api/v1/captures/text", json=product_body)

        assert duplicate_response.status_code == 200
        relationship = duplicate_response.json()["memories"][0]["relationships"][0]
        assert relationship["relationship_type"] == "tension"
        assert relationship["related_memory_id"] == distribution_response.json()["memories"][0]["id"]
        assert relation_detector.calls == 3
    finally:
        app.dependency_overrides.clear()
