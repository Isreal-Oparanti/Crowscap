from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.structured_outputs import (
    CaptureExtraction,
    ExtractedMemoryAtom,
    GroundedChatSynthesis,
)
from app.core.auth import CurrentUser, require_current_user
from app.db.base import Base
from app.db.models import Capture, ChatMessage, Conversation, Memory, Reminder, Source, UserPreference
from app.db.session import get_db
from app.main import app
from app.schemas.belief import BeliefAuditResponse, PublicEvidenceResult
from app.schemas.search import SearchResult
from app.services.belief_audit_service import get_belief_auditor
from app.services.chat_service import get_chat_conversation_responder, get_chat_synthesizer
from app.services.embedding_service import get_memory_embedder
from app.services.extraction_service import get_memory_extractor
from app.services.relationship_service import get_memory_relation_detector


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


class OrthogonalFakeEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeExtractor:
    def extract_text(
        self,
        *,
        text: str,
        intent_text: str | None = None,
        user_note: str | None = None,
    ) -> CaptureExtraction:
        return CaptureExtraction(
            source_title="Saved learning",
            inferred_intents=["remember"],
            memories=[
                ExtractedMemoryAtom(
                    memory_type="principle",
                    epistemic_label="advice",
                    content="Distribution should be considered while shaping the product.",
                    summary="Distribution informs product development.",
                    confidence="medium",
                    confidence_reason="The input presents this as advice.",
                    source_strength="moderate",
                )
            ],
        )


class FakeRelationDetector:
    def detect_for_memories(
        self,
        *,
        db: Session,
        new_memories: list[Memory],
        user_id: str | None = None,
    ) -> list:
        return []


class FakeSynthesizer:
    def synthesize(self, **kwargs) -> GroundedChatSynthesis:
        return GroundedChatSynthesis(
            answer=(
                "Your saved ideas suggest that reaching customers should be tested early, "
                "but they do not support using distribution to compensate for weak demand."
            ),
            knowledge_gaps=[
                "Your memories do not yet compare which channels fit this product."
            ],
            tensions=[
                "Product quality and early channel testing both matter, but their sequencing is contextual."
            ],
            next_step="Define one channel experiment and the demand signal it should test.",
        )


class FakeConversationResponder:
    def respond(self, **kwargs) -> str:
        return (
            "Leadership is not about becoming emotionless. It is about noticing the emotion, "
            "pausing before it drives the room, and choosing the response your team needs."
        )


class FakeBeliefAuditor:
    def audit(self, **kwargs) -> BeliefAuditResponse:
        return BeliefAuditResponse(
            topic="startup distribution",
            answer=(
                "Your saved distribution belief is useful, but it should be checked against "
                "where demand already exists and what evidence supports the channel."
            ),
            current_understanding="You currently connect distribution with early customer discovery.",
            strongest_saved_ideas=[
                "Distribution channels should be tested before launch."
            ],
            public_evidence_summary="Public leads add context, but they are source leads, not proof.",
            unsupported_or_weak_points=[
                "You have not saved evidence showing which channel fits your exact market."
            ],
            ideas_to_compare=[
                "Distribution can shape product, but product demand still matters."
            ],
            confidence="medium",
            confidence_reason="The audit has one saved idea and one public source lead.",
            next_questions=["Which channel are you testing this week?"],
            memories=[
                SearchResult(
                    memory_id="memory-1",
                    source_id="source-1",
                    source_type="text",
                    source_title="Distribution note",
                    memory_type="principle",
                    epistemic_label="advice",
                    content="Distribution channels should be tested before launch.",
                    summary=None,
                    confidence="medium",
                    confidence_reason=None,
                    source_strength="moderate",
                    similarity_score=0.8,
                    embedding_dimensions=2,
                )
            ],
            public_evidence=[
                PublicEvidenceResult(
                    title="Distribution evidence",
                    url="https://example.com/distribution",
                    snippet="A source lead about customer acquisition.",
                    source="example.com",
                    query="startup distribution evidence",
                    rank=1,
                )
            ],
            public_search_status="searched",
            public_search_message=None,
        )


def build_chat_db_override():
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

    app.dependency_overrides[require_current_user] = lambda: CurrentUser(
        id="test-user",
        email="test@example.com",
        name="Test User",
    )

    return override_db, testing_session


def test_acknowledgement_is_not_saved_as_memory() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "okay this makes sense thanks", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "acknowledge"
        assert payload["conversation_id"]
        assert payload["saved"] is False
        assert payload["capture"] is None

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        assert db.scalar(select(func.count(Conversation.id))) == 1
        assert db.scalar(select(func.count(ChatMessage.id))) == 2
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_explicit_preference_updates_profile_without_saving_memory() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": (
                    "I prefer short answers. Challenge my assumptions more. "
                    "I care mostly about startups and product. Don't show me weak "
                    "YouTube advice unless there is evidence."
                ),
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "acknowledge"
        assert payload["saved"] is False
        assert payload["capture"] is None
        assert payload["preference_updates"]
        assert payload["preferences"]["answer_style"] == "concise"
        assert payload["preferences"]["challenge_style"] == "direct"
        assert payload["preferences"]["evidence_strictness"] == "strict"
        assert "startups" in payload["preferences"]["topics_of_interest"]
        assert "youtube" in payload["preferences"]["source_preferences"]["avoid_weak"]

        db = testing_session()
        profile = db.scalar(select(UserPreference))
        assert profile is not None
        assert profile.answer_style == "concise"
        assert profile.challenge_style == "direct"
        assert profile.evidence_strictness == "strict"
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_get_preferences_returns_durable_profile() -> None:
    override_db, _testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "I prefer detailed answers and evidence-heavy audits.", "history": []},
        )
        assert response.status_code == 200

        preferences_response = client.get("/api/v1/preferences/me")
        assert preferences_response.status_code == 200
        payload = preferences_response.json()
        assert payload["answer_style"] == "detailed"
        assert payload["evidence_strictness"] == "strict"
    finally:
        app.dependency_overrides.clear()


def test_current_chat_question_uses_conversation_not_memory_search() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        first_response = client.post(
            "/api/v1/chat",
            json={"message": "Thank you", "history": []},
        )
        assert first_response.status_code == 200
        conversation_id = first_response.json()["conversation_id"]

        second_response = client.post(
            "/api/v1/chat",
            json={
                "message": "have i thanked you b4 in this chat?",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert second_response.status_code == 200
        payload = second_response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert payload["evidence"] == []
        assert "thanked me once" in payload["message"]

        current_response = client.get("/api/v1/chat/conversations/current")
        assert current_response.status_code == 200
        current_payload = current_response.json()
        assert current_payload["id"] == conversation_id
        assert len(current_payload["messages"]) == 4

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        assert db.scalar(select(func.count(ChatMessage.id))) == 4
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_self_question_uses_crowscap_capability_knowledge() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "what are you?", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "self"
        assert payload["saved"] is False
        assert payload["capture"] is None
        assert "private memory intelligence system" in payload["message"]
        assert "source-aware knowledge" in payload["message"]
        assert "I should stay quiet" not in payload["message"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_explicit_memory_message_uses_capture_pipeline() -> None:
    override_db, _testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_memory_extractor] = lambda: FakeExtractor()
    app.dependency_overrides[get_memory_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_memory_relation_detector] = lambda: FakeRelationDetector()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": (
                    "Remember this: distribution should be considered while shaping "
                    "the product, not only after launch."
                ),
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "capture"
        assert payload["saved"] is True
        assert len(payload["capture"]["memories"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_question_returns_synthesis_gaps_and_evidence_without_saving() -> None:
    override_db, testing_session = build_chat_db_override()
    db = testing_session()
    source = Source(source_type="text", title="Distribution note", user_id="test-user")
    db.add(source)
    db.flush()
    capture = Capture(
        source_id=source.id,
        user_id="test-user",
        status="ready",
        inferred_intents=["remember"],
    )
    db.add(capture)
    db.flush()
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        user_id="test-user",
        memory_type="principle",
        epistemic_label="advice",
        content="Test distribution channels early to learn how customers discover the product.",
        confidence="medium",
        source_strength="moderate",
        embedding_json=[1.0, 0.0],
    )
    db.add(memory)
    db.commit()
    db.close()

    embedder = FakeEmbedder()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_memory_embedder] = lambda: embedder
    app.dependency_overrides[get_chat_synthesizer] = lambda: FakeSynthesizer()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "How do I get my product to customers?", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "answer"
        assert payload["saved"] is False
        assert "reaching customers" in payload["message"]
        assert len(payload["evidence"]) == 1
        assert payload["knowledge_gaps"]
        assert payload["tensions"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 1
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_normal_advice_question_does_not_pull_weak_unrelated_memories() -> None:
    override_db, testing_session = build_chat_db_override()
    db = testing_session()
    source = Source(source_type="text", title="FoundrGeeks note", user_id="test-user")
    db.add(source)
    db.flush()
    capture = Capture(
        source_id=source.id,
        user_id="test-user",
        status="ready",
        inferred_intents=["remember"],
    )
    db.add(capture)
    db.flush()
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        user_id="test-user",
        memory_type="principle",
        epistemic_label="advice",
        content="FoundrGeeks matches founders with compatible co-founders and builders.",
        confidence="high",
        source_strength="moderate",
        embedding_json=[0.0, 1.0],
    )
    db.add(memory)
    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_memory_embedder] = lambda: OrthogonalFakeEmbedder()
    app.dependency_overrides[get_chat_conversation_responder] = lambda: FakeConversationResponder()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": (
                    "how can i be less emotional as a leader and still influence "
                    "and care for my team?"
                ),
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert payload["evidence"] == []
        assert "FoundrGeeks" not in payload["message"]
        assert "Leadership" in payload["message"]
    finally:
        app.dependency_overrides.clear()


def test_explicit_belief_audit_routes_to_audit_without_saving() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_belief_auditor] = lambda: FakeBeliefAuditor()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "audit what I believe about startup distribution", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "audit"
        assert payload["saved"] is False
        assert payload["audit"]["topic"] == "startup distribution"
        assert payload["audit"]["public_search_status"] == "searched"
        assert len(payload["audit"]["public_evidence"]) == 1

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_forget_capability_question_is_self_aware_without_searching() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "can you forget a memory?", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "forget"
        assert payload["saved"] is False
        assert "archive memories" in payload["message"]
        assert payload["evidence"] == []

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_topic_forget_returns_confirmation_candidates_not_audit() -> None:
    override_db, testing_session = build_chat_db_override()
    db = testing_session()
    source = Source(source_type="text", title="Distribution note", user_id="test-user")
    db.add(source)
    db.flush()
    capture = Capture(
        source_id=source.id,
        user_id="test-user",
        status="ready",
        inferred_intents=["remember"],
    )
    db.add(capture)
    db.flush()
    db.add(
        Memory(
            source_id=source.id,
            capture_id=capture.id,
            user_id="test-user",
            memory_type="principle",
            epistemic_label="advice",
            content="Distribution should be tested while shaping the product.",
            confidence="medium",
            source_strength="moderate",
            embedding_json=[1.0, 0.0],
        )
    )
    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_memory_embedder] = lambda: FakeEmbedder()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "forget what I know about distribution", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "forget"
        assert payload["saved"] is False
        assert payload["audit"] is None
        assert len(payload["evidence"]) == 1
        assert "I have not archived them yet" in payload["message"]
    finally:
        app.dependency_overrides.clear()


def test_reminder_with_note_saves_memory_and_sets_due_recall_time() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_memory_extractor] = lambda: FakeExtractor()
    app.dependency_overrides[get_memory_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_memory_relation_detector] = lambda: FakeRelationDetector()

    note = "Distribution should be considered while shaping the product, not only after launch."
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": f"remind me to revisit this in the next 1hr\n{note}",
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "reminder"
        assert payload["saved"] is True
        assert payload["capture"] is not None
        assert payload["reminder"]["save_as_memory"] is True

        db = testing_session()
        memory = db.scalar(select(Memory))
        reminder = db.scalar(select(Reminder))
        assert memory is not None
        assert reminder is not None
        assert reminder.memory_id == memory.id
        assert reminder.save_as_memory == 1
        assert memory.next_review_at == reminder.due_at
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_reminder_can_skip_semantic_memory_storage() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    note = "Check the deployment proof recording before submitting the hackathon."
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": f"remind me in the next 1hr, but don't save this information in my memory\n{note}",
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "reminder"
        assert payload["saved"] is False
        assert payload["capture"] is None
        assert payload["reminder"]["save_as_memory"] is False

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        reminder = db.scalar(select(Reminder))
        assert reminder is not None
        assert reminder.content == note
        assert reminder.save_as_memory == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_short_practical_reminder_is_not_saved_as_memory_by_default() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "can you remind me to take water in the next 5mins?",
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "reminder"
        assert payload["saved"] is False
        assert payload["capture"] is None
        assert payload["reminder"]["save_as_memory"] is False
        assert payload["reminder"]["content"] == "take water"

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        assert db.scalar(select(func.count(Reminder.id))) == 1
        db.close()
    finally:
        app.dependency_overrides.clear()
