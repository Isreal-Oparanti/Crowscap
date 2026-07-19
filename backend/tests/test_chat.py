from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.structured_outputs import (
    CaptureExtraction,
    ChatRoute,
    ExtractedMemoryAtom,
    GroundedChatSynthesis,
)
from app.core.auth import CurrentUser, require_current_user
from app.db.base import Base
from app.db.models import (
    Capture,
    ChatMessage,
    Conversation,
    Memory,
    MemoryArchiveEvent,
    Reminder,
    Source,
    UserPreference,
)
from app.db.session import get_db
from app.main import app
from app.schemas.belief import BeliefAuditResponse, PublicEvidenceResult
from app.schemas.capture import MemoryCardResponse, TextCaptureResponse
from app.schemas.search import SearchResponse, SearchResult
from app.services.belief_audit_service import get_belief_auditor
from app.services.chat_service import (
    QwenChatIntentRouter,
    _pack_memory_context,
    get_chat_conversation_responder,
    get_chat_router,
    get_chat_synthesizer,
)
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


class CapturingConversationResponder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def respond(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return "Thought-provoking means it makes you pause and think more carefully."


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


class FixedRouter:
    def __init__(self, action: str, *, reply: str | None = None) -> None:
        self.action = action
        self.reply = reply

    def route(self, **kwargs) -> ChatRoute:
        return ChatRoute(
            action=self.action,
            reply=self.reply,
            reason=f"Fixed test route: {self.action}.",
        )


class FakeRoutingClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def chat_json(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return self.payload


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


def test_first_message_question_reads_complete_persisted_history() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        first_response = client.post(
            "/api/v1/chat",
            json={"message": "heyy", "history": []},
        )
        assert first_response.status_code == 200
        conversation_id = first_response.json()["conversation_id"]

        for _ in range(7):
            filler_response = client.post(
                "/api/v1/chat",
                json={
                    "message": "okay",
                    "conversation_id": conversation_id,
                    "history": [],
                },
            )
            assert filler_response.status_code == 200

        question_response = client.post(
            "/api/v1/chat",
            json={
                "message": "I mean the very first thing I said in the beginning of our chat",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert question_response.status_code == 200
        payload = question_response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert payload["evidence"] == []
        assert 'Your first message in this chat was: "heyy"' in payload["message"]
        assert "what is still missing" not in payload["message"].lower()

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_bare_url_requires_confirmation_before_capture() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "https://example.com/research", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert payload["capture"] is None
        assert "I have not saved it yet" in payload["message"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_substantial_note_with_url_is_saved_as_text_not_link_preview(monkeypatch) -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_memory_extractor] = lambda: FakeExtractor()
    app.dependency_overrides[get_memory_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_memory_relation_detector] = lambda: FakeRelationDetector()

    def fail_url_capture(**kwargs) -> TextCaptureResponse:
        raise AssertionError("Mixed learning notes with links must not route to URL ingestion.")

    monkeypatch.setattr("app.services.chat_service.create_url_capture", fail_url_capture)

    note = (
        "One of the hardest parts of building a product is finding the right team to execute. "
        "Therefore we created FoundrGeeks, a network where founders find co-founders, developers, "
        "designers, operators, marketers, and skilled builders ready to collaborate. "
        "Start here: https://foundrgeeks.com Foundrgeeks (https://foundrgeeks.com/)"
    )

    try:
        client = TestClient(app)
        response = client.post("/api/v1/chat", json={"message": note, "history": []})

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "capture"
        assert payload["saved"] is True
        assert "I found this link" not in payload["message"]

        db = testing_session()
        source = db.scalar(select(Source))
        assert source is not None
        assert source.source_type == "text"
        assert source.raw_text is not None
        assert "finding the right team" in source.raw_text
        assert "https://foundrgeeks.com" in source.raw_text
        assert db.scalar(select(func.count(Memory.id))) == 1
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_explicit_save_link_with_url_still_uses_url_ingestion(monkeypatch) -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    captured_urls: list[str] = []
    captured_intents: list[str | None] = []

    def fake_create_url_capture(**kwargs) -> TextCaptureResponse:
        captured_urls.append(kwargs["payload"].url)
        captured_intents.append(kwargs["payload"].intent_text)
        return TextCaptureResponse(
            capture_id="capture-1",
            source_id="source-1",
            source_type="article",
            source_title="Example article",
            original_content="Example article body",
            status="ready",
            inferred_intents=["read_later"],
            memories=[
                MemoryCardResponse(
                    id="memory-1",
                    source_type="article",
                    memory_type="reference",
                    epistemic_label="source_summary",
                    content="Read the example article.",
                    summary=None,
                    confidence="high",
                    confidence_reason="The user explicitly asked Crowscap to save the link.",
                    source_strength="strong",
                    embedding_dimensions=2,
                    relationships=[],
                )
            ],
        )

    monkeypatch.setattr("app.services.chat_service.create_url_capture", fake_create_url_capture)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "save this link https://example.com/research", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "capture"
        assert payload["saved"] is True
        assert captured_urls == ["https://example.com/research"]
        assert captured_intents == ["save this link"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_confirmed_pending_url_is_captured(monkeypatch) -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    captured_urls: list[str] = []

    def fake_create_url_capture(**kwargs) -> TextCaptureResponse:
        captured_urls.append(kwargs["payload"].url)
        return TextCaptureResponse(
            capture_id="capture-1",
            source_id="source-1",
            source_type="article",
            source_title="Example article",
            original_content="Example article body",
            status="ready",
            inferred_intents=["read_later"],
            memories=[
                MemoryCardResponse(
                    id="memory-1",
                    source_type="article",
                    memory_type="reference",
                    epistemic_label="source_summary",
                    content="Read the example article.",
                    summary=None,
                    confidence="high",
                    confidence_reason="The user confirmed the link should be saved.",
                    source_strength="strong",
                    embedding_dimensions=2,
                    relationships=[],
                )
            ],
        )

    monkeypatch.setattr("app.services.chat_service.create_url_capture", fake_create_url_capture)

    try:
        client = TestClient(app)
        preview_response = client.post(
            "/api/v1/chat",
            json={"message": "https://example.com/research", "history": []},
        )
        assert preview_response.status_code == 200
        conversation_id = preview_response.json()["conversation_id"]

        capture_response = client.post(
            "/api/v1/chat",
            json={
                "message": "yes please",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert capture_response.status_code == 200
        payload = capture_response.json()
        assert payload["action"] == "capture"
        assert payload["saved"] is True
        assert captured_urls == ["https://example.com/research"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_semantic_pending_url_confirmation_is_captured(monkeypatch) -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    routing_client = FakeRoutingClient(
        {
            "action": "capture",
            "reply": None,
            "reason": "The user is informally confirming the pending video link.",
        }
    )
    app.dependency_overrides[get_chat_router] = lambda: QwenChatIntentRouter(routing_client)

    captured_urls: list[str] = []

    def fake_create_url_capture(**kwargs) -> TextCaptureResponse:
        captured_urls.append(kwargs["payload"].url)
        return TextCaptureResponse(
            capture_id="capture-1",
            source_id="source-1",
            source_type="youtube",
            source_title="Example video",
            original_content="Example transcript",
            status="ready",
            inferred_intents=["read_later"],
            memories=[
                MemoryCardResponse(
                    id="memory-1",
                    source_type="youtube",
                    memory_type="reference",
                    epistemic_label="source_summary",
                    content="Read the example video transcript.",
                    summary=None,
                    confidence="high",
                    confidence_reason="The user confirmed the video should be saved.",
                    source_strength="strong",
                    embedding_dimensions=2,
                    relationships=[],
                )
            ],
        )

    monkeypatch.setattr("app.services.chat_service.create_url_capture", fake_create_url_capture)

    try:
        client = TestClient(app)
        preview_response = client.post(
            "/api/v1/chat",
            json={
                "message": "https://youtube.com/shorts/kwQV9CqUj1M?si=test",
                "history": [],
            },
        )
        assert preview_response.status_code == 200
        conversation_id = preview_response.json()["conversation_id"]

        capture_response = client.post(
            "/api/v1/chat",
            json={
                "message": "absolutely, handle that video",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert capture_response.status_code == 200
        payload = capture_response.json()
        assert payload["action"] == "capture"
        assert payload["saved"] is True
        assert captured_urls == ["https://youtube.com/shorts/kwQV9CqUj1M?si=test"]
        assert len(routing_client.calls) == 1
        assert (
            "pending_url: https://youtube.com/shorts/kwQV9CqUj1M?si=test"
            in routing_client.calls[0]["user_prompt"]
        )

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_local_definition_after_capture_stays_in_current_context(monkeypatch) -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("answer")
    responder = CapturingConversationResponder()
    app.dependency_overrides[get_chat_conversation_responder] = lambda: responder

    def fail_memory_search(**kwargs) -> SearchResponse:
        raise AssertionError("Local definition follow-ups should not search long-term memory.")

    monkeypatch.setattr("app.services.chat_service.search_memories", fail_memory_search)

    db = testing_session()
    conversation = Conversation(user_id="test-user", title="YouTube note")
    source = Source(
        user_id="test-user",
        source_type="youtube",
        title="Sanctification short",
        raw_text="A short transcript about sanctification.",
        extracted_text_hash="youtube-hash",
    )
    db.add_all([conversation, source])
    db.flush()
    capture = Capture(
        user_id="test-user",
        source_id=source.id,
        status="ready",
        inferred_intents=["learned", "question"],
    )
    db.add(capture)
    db.flush()
    db.add_all(
        [
            Memory(
                user_id="test-user",
                source_id=source.id,
                capture_id=capture.id,
                memory_type="principle",
                epistemic_label="advice",
                content="Sanctification is portrayed as active and costly.",
                confidence="high",
                source_strength="moderate",
                embedding_json=[1.0, 0.0],
            ),
            ChatMessage(
                conversation_id=conversation.id,
                user_id="test-user",
                role="assistant",
                action="capture",
                content="I kept this as 7 distinct memories.",
                metadata_json={
                    "action": "capture",
                    "saved": True,
                    "capture": {
                        "capture_id": capture.id,
                        "source_id": source.id,
                        "source_type": "youtube",
                        "source_title": source.title,
                        "status": "ready",
                        "inferred_intents": ["learned", "question"],
                        "memories": [],
                    },
                },
            ),
            ChatMessage(
                conversation_id=conversation.id,
                user_id="test-user",
                role="user",
                content="hmmm this is deep",
            ),
            ChatMessage(
                conversation_id=conversation.id,
                user_id="test-user",
                role="assistant",
                content="I agree, it is thought-provoking.",
            ),
        ]
    )
    db.commit()
    conversation_id = conversation.id
    db.close()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "what is thought provoking?",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert payload["evidence"] == []
        assert responder.calls
        prompt_history = "\n".join(turn.content for turn in responder.calls[0]["history"])
        assert "Immediate context from the source the user just saved" in prompt_history
        assert "Sanctification is portrayed as active and costly" in prompt_history
    finally:
        app.dependency_overrides.clear()


def test_old_capture_context_is_not_injected_into_unrelated_later_chat() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("conversation")
    responder = CapturingConversationResponder()
    app.dependency_overrides[get_chat_conversation_responder] = lambda: responder

    db = testing_session()
    conversation = Conversation(user_id="test-user", title="Old capture")
    source = Source(
        user_id="test-user",
        source_type="youtube",
        title="Old theology short",
        raw_text="Old transcript.",
        extracted_text_hash="old-youtube-hash",
    )
    db.add_all([conversation, source])
    db.flush()
    capture = Capture(user_id="test-user", source_id=source.id, status="ready")
    db.add(capture)
    db.flush()
    db.add(
        Memory(
            user_id="test-user",
            source_id=source.id,
            capture_id=capture.id,
            memory_type="claim",
            epistemic_label="opinion",
            content="An old unrelated memory should not leak into new chat.",
            confidence="medium",
            source_strength="moderate",
            embedding_json=[1.0, 0.0],
        )
    )
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            user_id="test-user",
            role="assistant",
            action="capture",
            content="I kept this as 1 distinct memories.",
            metadata_json={
                "action": "capture",
                "saved": True,
                "capture": {"capture_id": capture.id, "source_id": source.id},
            },
        )
    )
    for index in range(8):
        db.add(
            ChatMessage(
                conversation_id=conversation.id,
                user_id="test-user",
                role="user" if index % 2 == 0 else "assistant",
                content=f"later unrelated turn {index}",
            )
        )
    db.commit()
    conversation_id = conversation.id
    db.close()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "tell me more about launch planning",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert response.status_code == 200
        assert responder.calls
        prompt_history = "\n".join(turn.content for turn in responder.calls[0]["history"])
        assert "Immediate context from the source the user just saved" not in prompt_history
        assert "old unrelated memory" not in prompt_history.lower()
    finally:
        app.dependency_overrides.clear()


def test_memory_context_pack_removes_duplicates_and_respects_priority() -> None:
    override_db, testing_session = build_chat_db_override()
    db = testing_session()
    source = Source(user_id="test-user", source_type="text", title="Distribution")
    db.add(source)
    db.flush()
    capture = Capture(user_id="test-user", source_id=source.id, status="ready")
    db.add(capture)
    db.flush()
    high_memory = Memory(
        user_id="test-user",
        source_id=source.id,
        capture_id=capture.id,
        memory_type="principle",
        epistemic_label="advice",
        content="Distribution should shape product development before launch.",
        confidence="high",
        source_strength="strong",
        embedding_json=[1.0, 0.0],
    )
    low_memory = Memory(
        user_id="test-user",
        source_id=source.id,
        capture_id=capture.id,
        memory_type="claim",
        epistemic_label="opinion",
        content="Distribution should shape product development before launch.",
        confidence="low",
        source_strength="weak",
        embedding_json=[1.0, 0.0],
    )
    db.add_all([high_memory, low_memory])
    db.commit()

    search = SearchResponse(
        query="distribution",
        min_score=0.25,
        candidate_count=2,
        embedded_candidate_count=2,
        returned_count=2,
        top_score=0.9,
        results=[
            SearchResult(
                memory_id=low_memory.id,
                source_id=source.id,
                source_type="text",
                source_title="Distribution",
                memory_type="claim",
                epistemic_label="opinion",
                content=low_memory.content,
                summary=None,
                confidence="low",
                confidence_reason=None,
                source_strength="weak",
                similarity_score=0.91,
                embedding_dimensions=2,
            ),
            SearchResult(
                memory_id=high_memory.id,
                source_id=source.id,
                source_type="text",
                source_title="Distribution",
                memory_type="principle",
                epistemic_label="advice",
                content=high_memory.content,
                summary=None,
                confidence="high",
                confidence_reason=None,
                source_strength="strong",
                similarity_score=0.9,
                embedding_dimensions=2,
            ),
        ],
    )

    packed = _pack_memory_context(db=db, search=search, max_tokens=2_000)

    assert packed.returned_count == 1
    assert packed.results[0].memory_id == high_memory.id
    db.close()


def test_pending_url_does_not_swallow_new_short_note(monkeypatch) -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("capture")

    captured_texts: list[str] = []

    def fail_url_capture(**kwargs) -> TextCaptureResponse:
        raise AssertionError("A new note should not confirm the older pending link.")

    def fake_create_text_capture(**kwargs) -> TextCaptureResponse:
        captured_texts.append(kwargs["payload"].content)
        return TextCaptureResponse(
            capture_id="capture-1",
            source_id="source-1",
            source_type="text",
            source_title="Short note",
            original_content=kwargs["payload"].content,
            status="ready",
            inferred_intents=["remember"],
            memories=[
                MemoryCardResponse(
                    id="memory-1",
                    source_type="text",
                    memory_type="claim",
                    epistemic_label="opinion",
                    content="Polling can fail quickly.",
                    summary=None,
                    confidence="medium",
                    confidence_reason="The user stated it as a short learning note.",
                    source_strength="moderate",
                    embedding_dimensions=2,
                    relationships=[],
                )
            ],
        )

    monkeypatch.setattr("app.services.chat_service.create_url_capture", fail_url_capture)
    monkeypatch.setattr("app.services.chat_service.create_text_capture", fake_create_text_capture)

    try:
        client = TestClient(app)
        preview_response = client.post(
            "/api/v1/chat",
            json={"message": "https://example.com/research", "history": []},
        )
        assert preview_response.status_code == 200
        conversation_id = preview_response.json()["conversation_id"]

        capture_response = client.post(
            "/api/v1/chat",
            json={
                "message": "I learned polling can fail quickly",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert capture_response.status_code == 200
        payload = capture_response.json()
        assert payload["action"] == "capture"
        assert payload["saved"] is True
        assert captured_texts == ["I learned polling can fail quickly"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_short_capture_route_without_pending_target_returns_helpful_reply() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("capture")

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "yes please", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert payload["capture"] is None
        assert "actual content" in payload["message"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_declining_pending_url_does_not_capture_later_yes(monkeypatch) -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_router] = lambda: QwenChatIntentRouter(
        FakeRoutingClient(
            {
                "action": "acknowledge",
                "reply": "Sure.",
                "reason": "Plain confirmation after the pending link was declined.",
            }
        )
    )

    def fail_url_capture(**kwargs) -> TextCaptureResponse:
        raise AssertionError("Declined links must not remain pending.")

    monkeypatch.setattr("app.services.chat_service.create_url_capture", fail_url_capture)

    try:
        client = TestClient(app)
        preview_response = client.post(
            "/api/v1/chat",
            json={"message": "https://example.com/research", "history": []},
        )
        conversation_id = preview_response.json()["conversation_id"]

        decline_response = client.post(
            "/api/v1/chat",
            json={
                "message": "no thanks",
                "conversation_id": conversation_id,
                "history": [],
            },
        )
        assert decline_response.status_code == 200
        assert decline_response.json()["saved"] is False
        assert "unsaved" in decline_response.json()["message"]

        later_response = client.post(
            "/api/v1/chat",
            json={
                "message": "yes please",
                "conversation_id": conversation_id,
                "history": [],
            },
        )
        assert later_response.status_code == 200
        payload = later_response.json()
        assert payload["saved"] is False
        assert payload["capture"] is None

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_short_clarification_after_assistant_question_stays_conversational() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "its a company",
                "history": [
                    {"role": "user", "content": "ascentrade"},
                    {
                        "role": "assistant",
                        "content": "I'm not familiar with Ascentrade. Could you clarify what it is?",
                    },
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert "Got it" in payload["message"]
        assert "company" in payload["message"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_short_clarification_uses_persisted_conversation_history() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    db = testing_session()
    conversation = Conversation(user_id="test-user", title="Ascentrade")
    db.add(conversation)
    db.flush()
    db.add_all(
        [
            ChatMessage(
                conversation_id=conversation.id,
                user_id="test-user",
                role="user",
                content="ascentrade",
            ),
            ChatMessage(
                conversation_id=conversation.id,
                user_id="test-user",
                role="assistant",
                content="I'm not familiar with Ascentrade. Could you clarify what it is?",
            ),
        ]
    )
    db.commit()
    conversation_id = conversation.id
    db.close()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "its a company",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert "Got it" in payload["message"]
        assert "company" in payload["message"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_whatsapp_invite_link_is_rejected_without_capture() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "https://chat.whatsapp.com/LK0yk9lerym0VmBi7C8EF7",
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "conversation"
        assert payload["saved"] is False
        assert payload["capture"] is None
        assert "WhatsApp group invite links" in payload["message"]

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_save_that_captures_previous_assistant_response() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_memory_extractor] = lambda: FakeExtractor()
    app.dependency_overrides[get_memory_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_memory_relation_detector] = lambda: FakeRelationDetector()

    db = testing_session()
    conversation = Conversation(user_id="test-user", title="Product launch")
    db.add(conversation)
    db.flush()
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            user_id="test-user",
            role="assistant",
            content=(
                "Launching a product strongly means knowing your first users, "
                "choosing one focused channel, and planning the day-two feedback loop."
            ),
        )
    )
    conversation_id = conversation.id
    db.commit()
    db.close()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "save that", "conversation_id": conversation_id, "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "capture"
        assert payload["saved"] is True
        assert payload["capture"] is not None

        db = testing_session()
        assert db.scalar(select(func.count(Capture.id))) == 1
        assert db.scalar(select(func.count(Memory.id))) == 1
        source = db.scalar(select(Source))
        assert source is not None
        assert source.title.startswith("Crowscap conversation -")
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_forget_what_you_just_saved_archives_recent_pdf_capture() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db

    db = testing_session()
    conversation = Conversation(user_id="test-user", title="PDF upload")
    source = Source(
        user_id="test-user",
        source_type="pdf",
        title="Malaria Surveillance.pdf",
        raw_text="Malaria surveillance source text.",
        extracted_text_hash="pdf-hash",
    )
    db.add_all([conversation, source])
    db.flush()
    capture = Capture(
        user_id="test-user",
        source_id=source.id,
        status="ready",
        inferred_intents=["learned", "reference"],
    )
    db.add(capture)
    db.flush()
    db.add_all(
        [
            Memory(
                user_id="test-user",
                source_id=source.id,
                capture_id=capture.id,
                memory_type="claim",
                epistemic_label="factual_claim",
                content="Malaria surveillance relies on timely case reporting.",
                confidence="high",
                source_strength="strong",
                embedding_json=[1.0, 0.0],
            ),
            Memory(
                user_id="test-user",
                source_id=source.id,
                capture_id=capture.id,
                memory_type="principle",
                epistemic_label="framework",
                content="Surveillance data should guide malaria response planning.",
                confidence="high",
                source_strength="strong",
                embedding_json=[1.0, 0.0],
            ),
            ChatMessage(
                conversation_id=conversation.id,
                user_id="test-user",
                role="assistant",
                action="capture",
                content="I kept this as 2 distinct memories.",
                metadata_json={
                    "action": "capture",
                    "saved": True,
                    "capture": {
                        "capture_id": capture.id,
                        "source_id": source.id,
                        "source_type": "pdf",
                        "source_title": source.title,
                        "status": "ready",
                        "inferred_intents": ["learned", "reference"],
                        "memories": [],
                    },
                },
            ),
        ]
    )
    conversation_id = conversation.id
    db.commit()
    db.close()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "can you remove what you just saved from my memory?",
                "conversation_id": conversation_id,
                "history": [],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "forget"
        assert payload["saved"] is False
        assert "Malaria Surveillance.pdf" in payload["message"]

        db = testing_session()
        statuses = list(db.scalars(select(Memory.status).order_by(Memory.content)))
        assert statuses == ["archived", "archived"]
        assert db.scalar(select(func.count(MemoryArchiveEvent.id))) == 2
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_self_question_uses_crowscap_capability_knowledge() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("self")

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


def test_typo_self_question_still_uses_crowscap_identity() -> None:
    override_db, testing_session = build_chat_db_override()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("self")

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "what is you?", "history": []},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "self"
        assert payload["saved"] is False
        assert "private memory intelligence system" in payload["message"]
        assert "I don’t have memory between conversations" not in payload["message"]
        assert "I don't have memory between conversations" not in payload["message"]
        assert "generic chat assistant" not in payload["message"].lower()

        db = testing_session()
        assert db.scalar(select(func.count(Memory.id))) == 0
        assert db.scalar(select(func.count(Capture.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_semantic_router_handles_indirect_identity_questions() -> None:
    fake_client = FakeRoutingClient(
        {
            "action": "self",
            "reply": None,
            "reason": "The user is asking what Crowscap is despite informal wording.",
        }
    )
    router = QwenChatIntentRouter(client=fake_client)

    route = router.route(message="can you explain yourself a bit?", history=[])

    assert route.action == "self"
    assert len(fake_client.calls) == 1
    prompt = fake_client.calls[0]["user_prompt"]
    assert "regardless of exact phrasing, typos, informal language" in prompt
    assert "what's your purpose?" in prompt


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
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("conversation")
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
    app.dependency_overrides[get_chat_router] = lambda: FixedRouter("conversation")
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
