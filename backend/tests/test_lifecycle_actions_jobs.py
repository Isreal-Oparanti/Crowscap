from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    ActionItem,
    Capture,
    Memory,
    MemoryArchiveEvent,
    MemoryRelation,
    ProcessingJob,
    Source,
    utc_now,
)
from app.schemas.action import CreateActionFromMemoryRequest, UpdateActionItemRequest
from app.schemas.capture import UrlCaptureRequest
from app.schemas.memory import ArchiveMemoryRequest
from app.services.action_service import (
    create_action_from_memory,
    list_action_suggestions,
    update_action_item,
)
from app.services.job_service import create_url_capture_job, get_processing_job
from app.services.memory_lifecycle_service import (
    archive_memory,
    list_archive_candidates,
    list_compression_candidates,
    restore_memory,
)


def build_db() -> tuple[sessionmaker[Session], Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session, testing_session()


def seed_capture(db: Session) -> tuple[Source, Capture]:
    source = Source(source_type="text", title="Distribution note", raw_text="raw note")
    db.add(source)
    db.flush()
    capture = Capture(source_id=source.id, inferred_intents=["remember"], status="ready")
    db.add(capture)
    db.flush()
    return source, capture


def make_memory(
    db: Session,
    *,
    source: Source,
    capture: Capture,
    content: str,
    memory_type: str = "principle",
    confidence: str = "medium",
    source_strength: str = "moderate",
    created_days_ago: int = 0,
) -> Memory:
    memory = Memory(
        source_id=source.id,
        capture_id=capture.id,
        memory_type=memory_type,
        epistemic_label="advice",
        content=content,
        confidence=confidence,
        source_strength=source_strength,
        next_review_at=utc_now(),
    )
    if created_days_ago:
        memory.created_at = utc_now() - timedelta(days=created_days_ago)
        memory.updated_at = memory.created_at
    db.add(memory)
    db.flush()
    return memory


def test_url_capture_job_is_persisted_for_polling() -> None:
    _testing_session, db = build_db()
    response = create_url_capture_job(
        db=db,
        payload=UrlCaptureRequest(
            url="https://example.com/article",
            user_note="Read later",
        ),
    )

    stored = get_processing_job(db=db, job_id=response.job_id)

    assert response.status == "queued"
    assert response.status_url == f"/api/v1/jobs/{response.job_id}"
    assert stored.status == "queued"
    assert stored.step == "queued"
    persisted_job = db.get(ProcessingJob, response.job_id)
    assert persisted_job is not None
    assert persisted_job.payload_json["url"] == "https://example.com/article"


def test_action_suggestion_can_be_promoted_and_completed() -> None:
    _testing_session, db = build_db()
    source, capture = seed_capture(db)
    action_memory = make_memory(
        db,
        source=source,
        capture=capture,
        memory_type="action",
        content="Test one distribution channel with five real users this week.",
        confidence="high",
    )
    make_memory(
        db,
        source=source,
        capture=capture,
        content="Distribution should be treated as learning, not a later campaign.",
    )
    db.commit()

    suggestions = list_action_suggestions(db=db)
    created = create_action_from_memory(
        db=db,
        memory_id=action_memory.id,
        payload=CreateActionFromMemoryRequest(due_at=utc_now() + timedelta(days=2)),
    )
    updated = update_action_item(
        db=db,
        action_id=created.id,
        payload=UpdateActionItemRequest(status="done"),
    )

    assert suggestions.count == 1
    assert suggestions.suggestions[0].memory_id == action_memory.id
    assert created.status == "planned"
    assert created.source_id == source.id
    assert updated.status == "done"
    assert updated.completed_at is not None
    assert db.scalar(select(ActionItem).where(ActionItem.memory_id == action_memory.id)) is not None


def test_archive_and_restore_memory_changes_active_lifecycle_state() -> None:
    _testing_session, db = build_db()
    source, capture = seed_capture(db)
    memory = make_memory(
        db,
        source=source,
        capture=capture,
        content="This is no longer useful.",
    )
    db.commit()

    archived = archive_memory(
        db=db,
        memory_id=memory.id,
        payload=ArchiveMemoryRequest(reason="user_dismissed", note="Do not show again."),
    )
    restored = restore_memory(db=db, memory_id=memory.id)

    stored_memory = db.get(Memory, memory.id)
    assert stored_memory is not None
    assert archived.previous_status == "active"
    assert archived.new_status == "archived"
    assert restored.previous_status == "archived"
    assert restored.new_status == "active"
    assert stored_memory.status == "active"
    assert stored_memory.next_review_at is not None
    assert len(db.scalars(select(MemoryArchiveEvent)).all()) == 2


def test_archive_candidates_surface_weak_old_unreviewed_memories() -> None:
    _testing_session, db = build_db()
    source, capture = seed_capture(db)
    weak_memory = make_memory(
        db,
        source=source,
        capture=capture,
        content="A single anecdote that may not deserve active recall forever.",
        confidence="low",
        source_strength="weak",
        created_days_ago=45,
    )
    db.commit()

    candidates = list_archive_candidates(db=db, min_age_days=30)

    assert candidates.count == 1
    assert candidates.candidates[0].memory_id == weak_memory.id
    assert "low confidence" in candidates.candidates[0].reasons
    assert "weak source strength" in candidates.candidates[0].reasons


def test_compression_candidates_surface_related_memory_clusters() -> None:
    _testing_session, db = build_db()
    source, capture = seed_capture(db)
    anchor = make_memory(
        db,
        source=source,
        capture=capture,
        content="Distribution should be learned through early experiments.",
    )
    related_one = make_memory(
        db,
        source=source,
        capture=capture,
        content="Early channel tests can shape product direction.",
    )
    related_two = make_memory(
        db,
        source=source,
        capture=capture,
        content="Distribution is part of product learning.",
    )
    db.add_all(
        [
            MemoryRelation(
                source_memory_id=anchor.id,
                target_memory_id=related_one.id,
                relation_type="confirms",
                strength="moderate",
                created_by="test",
            ),
            MemoryRelation(
                source_memory_id=anchor.id,
                target_memory_id=related_two.id,
                relation_type="extends",
                strength="moderate",
                created_by="test",
            ),
        ]
    )
    db.commit()

    candidates = list_compression_candidates(db=db)

    assert candidates.count >= 1
    assert candidates.candidates[0].memory_id == anchor.id
    assert candidates.candidates[0].related_count == 2
    assert set(candidates.candidates[0].related_memory_ids) == {related_one.id, related_two.id}
