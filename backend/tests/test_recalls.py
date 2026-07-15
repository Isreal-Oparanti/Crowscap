from collections.abc import Generator
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.ai.structured_outputs import RecallEvaluation
from app.db.models import Capture, Memory, MemoryRelation, RecallReview, Reminder, Source, utc_now
from app.db.session import get_db
from app.main import app
from app.services.recall_evaluation_service import get_recall_evaluator


def build_recall_db_override():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    now = utc_now()
    db = testing_session()
    source = Source(source_type="text", title="Distribution note")
    db.add(source)
    db.flush()
    capture = Capture(source_id=source.id, inferred_intents=["remember"], status="ready")
    db.add(capture)
    db.flush()

    very_due = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="principle",
        epistemic_label="advice",
        content="Distribution should be tested early.",
        confidence="medium",
        source_strength="moderate",
        next_review_at=now - timedelta(hours=3),
        review_count=1,
        recall_score=0.6,
    )
    less_due = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="warning",
        epistemic_label="advice",
        content="Distribution cannot rescue a product nobody wants.",
        confidence="medium",
        source_strength="moderate",
        next_review_at=now - timedelta(hours=1),
        review_count=0,
        recall_score=0.5,
    )
    future = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="action",
        epistemic_label="advice",
        content="Test one acquisition channel after product usage is real.",
        confidence="high",
        source_strength="moderate",
        next_review_at=now + timedelta(hours=6),
        review_count=0,
        recall_score=0.5,
    )
    db.add_all([very_due, less_due, future])
    db.flush()
    db.add(
        MemoryRelation(
            source_memory_id=less_due.id,
            target_memory_id=very_due.id,
            relation_type="tension",
            strength="moderate",
            explanation="One memory emphasizes product demand while the other emphasizes early distribution testing.",
            created_by="test",
        )
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


def test_due_recalls_returns_overdue_memories_with_relationships() -> None:
    app.dependency_overrides[get_db] = build_recall_db_override()

    try:
        client = TestClient(app)
        response = client.get("/api/v1/recalls/due")

        assert response.status_code == 200
        payload = response.json()
        assert payload["due_count"] == 2
        assert [memory["content"] for memory in payload["memories"]] == [
            "Distribution should be tested early.",
            "Distribution cannot rescue a product nobody wants.",
        ]
        assert payload["memories"][0]["overdue_seconds"] >= payload["memories"][1]["overdue_seconds"]
        assert payload["memories"][0]["relationships"][0]["relationship_type"] == "tension"
        assert payload["memories"][0]["relationships"][0]["direction"] == "incoming"
        assert payload["memories"][1]["relationships"][0]["direction"] == "outgoing"
        assert "related view" in payload["memories"][0]["recall_prompt"]
        assert "not as a verified fact" in payload["memories"][0]["epistemic_caution"]
    finally:
        app.dependency_overrides.clear()


class FakeRecallEvaluator:
    def evaluate(self, **kwargs) -> RecallEvaluation:
        return RecallEvaluation(
            score=0.78,
            rating="solid",
            feedback="You recovered the central idea and explained its practical purpose.",
            understanding_summary=(
                "Distribution testing is useful because it reveals how a product reaches "
                "real customers while the product is still being shaped."
            ),
            knowledge_gaps=[
                "You did not explain how product demand changes the value of channel testing."
            ],
            context_to_consider=[
                "This is advice from a moderate-strength source, not a universal law."
            ],
            next_question="What signal would show that a channel is reaching the right customers?",
        )


def test_recall_answer_is_persisted_and_rescheduled() -> None:
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
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="principle",
        epistemic_label="advice",
        content="Distribution should be tested early.",
        confidence="medium",
        source_strength="moderate",
        next_review_at=utc_now() - timedelta(hours=2),
        review_count=0,
        recall_score=0.5,
    )
    db.add(memory)
    db.commit()
    memory_id = memory.id
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_recall_evaluator] = lambda: FakeRecallEvaluator()

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/recalls/{memory_id}/answer",
            json={
                "answer": (
                    "Testing distribution early shows whether the team can reach the "
                    "customers it intends to serve before launch."
                ),
                "self_rating": 3,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["rating"] == "solid"
        assert payload["review_count"] == 1
        assert payload["knowledge_gaps"]
        assert payload["context_to_consider"]

        db = testing_session()
        stored_memory = db.get(Memory, memory_id)
        assert stored_memory is not None
        assert stored_memory.review_count == 1
        assert stored_memory.last_reviewed_at is not None
        assert stored_memory.next_review_at > stored_memory.last_reviewed_at
        assert db.scalar(select(func.count(RecallReview.id))) == 1
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_quick_recall_applied_reschedules_without_qwen() -> None:
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
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="action",
        epistemic_label="advice",
        content="Test one acquisition channel this week.",
        confidence="medium",
        source_strength="moderate",
        next_review_at=utc_now() - timedelta(hours=2),
        review_count=0,
        recall_score=0.5,
    )
    db.add(memory)
    db.commit()
    memory_id = memory.id
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/recalls/{memory_id}/quick",
            json={"action": "applied"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "applied"
        assert payload["review_count"] == 1
        assert payload["recall_score"] == 0.9

        db = testing_session()
        stored_memory = db.get(Memory, memory_id)
        assert stored_memory is not None
        assert stored_memory.review_count == 1
        assert stored_memory.last_reviewed_at is not None
        assert stored_memory.next_review_at > stored_memory.last_reviewed_at
        assert db.scalar(select(func.count(RecallReview.id))) == 1
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_quick_recall_not_now_defers_without_counting_as_review() -> None:
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
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="principle",
        epistemic_label="advice",
        content="Distribution should be considered before launch.",
        confidence="medium",
        source_strength="moderate",
        next_review_at=utc_now() - timedelta(hours=2),
        review_count=2,
        recall_score=0.61,
    )
    db.add(memory)
    db.commit()
    memory_id = memory.id
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/recalls/{memory_id}/quick",
            json={"action": "not_now"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "not_now"
        assert payload["review_count"] == 2
        assert payload["recall_score"] == 0.61

        db = testing_session()
        stored_memory = db.get(Memory, memory_id)
        assert stored_memory is not None
        assert stored_memory.review_count == 2
        assert stored_memory.last_reviewed_at is None
        assert stored_memory.next_review_at is not None
        assert stored_memory.next_review_at.replace(tzinfo=None) > utc_now().replace(tzinfo=None)
        assert db.scalar(select(func.count(RecallReview.id))) == 0
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_due_recalls_includes_due_non_memory_reminders() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    reminder = Reminder(
        content="Check the deployment proof recording.",
        due_at=utc_now() - timedelta(minutes=5),
        status="scheduled",
        save_as_memory=0,
    )
    db.add(reminder)
    db.commit()
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get("/api/v1/recalls/due")

        assert response.status_code == 200
        payload = response.json()
        assert payload["due_count"] == 1
        assert payload["memories"] == []
        assert payload["reminders"][0]["content"] == "Check the deployment proof recording."
        assert payload["reminders"][0]["save_as_memory"] is False
        with testing_session() as db:
            assert db.scalar(select(func.count(RecallReview.id))) == 0
    finally:
        app.dependency_overrides.clear()


def test_complete_due_reminder_removes_it_from_recall_queue() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    reminder = Reminder(
        content="Take water.",
        due_at=utc_now() - timedelta(minutes=2),
        status="scheduled",
        save_as_memory=0,
    )
    db.add(reminder)
    db.commit()
    reminder_id = reminder.id
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        complete_response = client.post(f"/api/v1/recalls/reminders/{reminder_id}/complete")

        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"

        due_response = client.get("/api/v1/recalls/due")
        assert due_response.status_code == 200
        due_payload = due_response.json()
        assert due_payload["due_count"] == 0
        assert due_payload["reminders"] == []
        with testing_session() as db:
            assert db.scalar(select(func.count(RecallReview.id))) == 0
    finally:
        app.dependency_overrides.clear()


def test_snooze_due_reminder_moves_it_out_of_recall_without_history() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    reminder = Reminder(
        content="Apply for the endorsement registration.",
        due_at=utc_now() - timedelta(minutes=3),
        status="scheduled",
        save_as_memory=0,
    )
    db.add(reminder)
    db.commit()
    reminder_id = reminder.id
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        snooze_response = client.post(
            f"/api/v1/recalls/reminders/{reminder_id}/snooze",
            json={"minutes": 60},
        )

        assert snooze_response.status_code == 200
        snoozed_payload = snooze_response.json()
        assert snoozed_payload["status"] == "scheduled"

        due_response = client.get("/api/v1/recalls/due")
        assert due_response.status_code == 200
        due_payload = due_response.json()
        assert due_payload["due_count"] == 0
        assert due_payload["reminders"] == []
        with testing_session() as db:
            stored = db.get(Reminder, reminder_id)
            assert stored is not None
            assert stored.due_at.replace(tzinfo=None) > utc_now().replace(tzinfo=None)
            assert db.scalar(select(func.count(RecallReview.id))) == 0
    finally:
        app.dependency_overrides.clear()


def test_due_recalls_does_not_duplicate_memory_linked_reminders() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    source = Source(source_type="text", title="Scheduled note")
    db.add(source)
    db.flush()
    capture = Capture(source_id=source.id, status="ready", inferred_intents=["remember"])
    db.add(capture)
    db.flush()
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type="principle",
        epistemic_label="advice",
        content="Schedule product distribution thinking before launch.",
        confidence="medium",
        source_strength="moderate",
        next_review_at=utc_now() - timedelta(minutes=5),
        recall_score=0.5,
    )
    db.add(memory)
    db.flush()
    db.add(
        Reminder(
            content="Schedule product distribution thinking before launch.",
            due_at=memory.next_review_at,
            status="scheduled",
            save_as_memory=1,
            memory_id=memory.id,
        )
    )
    db.commit()
    db.close()

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get("/api/v1/recalls/due")

        assert response.status_code == 200
        payload = response.json()
        assert payload["due_count"] == 1
        assert len(payload["memories"]) == 1
        assert payload["reminders"] == []
    finally:
        app.dependency_overrides.clear()
