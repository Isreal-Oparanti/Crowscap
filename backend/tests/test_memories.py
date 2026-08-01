from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.core.auth import CurrentUser, require_current_user
from app.db.base import Base
from app.db.models import (
    ActionItem,
    Capture,
    Memory,
    MemoryArchiveEvent,
    MemoryPerspectiveNote,
    MemoryRelation,
    RecallReview,
    Reminder,
    Source,
)
from app.db.session import get_db
from app.main import app


TEST_USER_ID = "test-user"


def override_auth() -> CurrentUser:
    return CurrentUser(id=TEST_USER_ID, email="test@example.com", name="Test User")


def test_delete_memory_removes_memory_and_dependent_rows() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    source = Source(user_id=TEST_USER_ID, source_type="text", title="Decision note")
    db.add(source)
    db.flush()
    capture = Capture(user_id=TEST_USER_ID, source_id=source.id, inferred_intents=["remember"], status="ready")
    db.add(capture)
    db.flush()
    memory = Memory(
        user_id=TEST_USER_ID,
        source_id=source.id,
        capture_id=capture.id,
        memory_type="principle",
        content="Fast reversible decisions compound learning.",
        confidence="high",
        source_strength="moderate",
    )
    other_memory = Memory(
        user_id=TEST_USER_ID,
        source_id=source.id,
        capture_id=capture.id,
        memory_type="claim",
        content="A second memory should remain intact.",
        confidence="medium",
        source_strength="moderate",
    )
    db.add_all([memory, other_memory])
    db.flush()
    db.add_all(
        [
            RecallReview(
                user_id=TEST_USER_ID,
                memory_id=memory.id,
                answer_text="Reviewed",
                evaluation_score=0.8,
                rating="good",
                feedback="Solid",
                understanding_summary="Understood",
                next_review_at=datetime.now(timezone.utc),
            ),
            MemoryArchiveEvent(
                user_id=TEST_USER_ID,
                memory_id=memory.id,
                previous_status="active",
                new_status="archived",
                reason="user_dismissed",
            ),
            MemoryPerspectiveNote(
                user_id=TEST_USER_ID,
                memory_id=memory.id,
                perspective_type="counterpoint",
                title="Consider reversibility",
                content="Some decisions are not reversible.",
                surface_after_at=datetime.now(timezone.utc),
            ),
            MemoryRelation(
                user_id=TEST_USER_ID,
                source_memory_id=memory.id,
                target_memory_id=other_memory.id,
                relation_type="supports",
                strength="moderate",
            ),
            Reminder(
                user_id=TEST_USER_ID,
                memory_id=memory.id,
                content="Review decision idea",
                due_at=datetime.now(timezone.utc),
            ),
            ActionItem(
                user_id=TEST_USER_ID,
                memory_id=memory.id,
                title="Apply decision idea",
            ),
        ]
    )
    memory_id = memory.id
    other_memory_id = other_memory.id
    db.commit()
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_current_user] = override_auth

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/memories/{memory_id}")

        assert response.status_code == 204

        check_db = testing_session()
        try:
            assert check_db.get(Memory, memory_id) is None
            assert check_db.get(Memory, other_memory_id) is not None
            assert check_db.scalars(select(RecallReview).where(RecallReview.memory_id == memory_id)).all() == []
            assert check_db.scalars(select(MemoryArchiveEvent).where(MemoryArchiveEvent.memory_id == memory_id)).all() == []
            assert check_db.scalars(select(MemoryPerspectiveNote).where(MemoryPerspectiveNote.memory_id == memory_id)).all() == []
            assert check_db.scalars(
                select(MemoryRelation).where(
                    (MemoryRelation.source_memory_id == memory_id)
                    | (MemoryRelation.target_memory_id == memory_id)
                )
            ).all() == []
            assert check_db.scalars(select(Reminder).where(Reminder.memory_id == memory_id)).all() == []
            assert check_db.scalars(select(ActionItem).where(ActionItem.memory_id == memory_id)).all() == []
        finally:
            check_db.close()
    finally:
        app.dependency_overrides.clear()
