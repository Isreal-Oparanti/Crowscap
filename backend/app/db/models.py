from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base
from app.db.vector import QWEN_EMBEDDING_DIMENSIONS

# `embedding_vector` (below, on Memory) used to exist ONLY as a raw-SQL
# managed Postgres column (see db/vector.py's ensure_postgres_vector_schema
# / update_memory_embedding_vector) -- it was never declared on the ORM
# model at all, so nothing here could query, select, or even know the
# column existed; every read/write to it had to go through hand-written
# SQL strings. Declare it properly so the ORM is aware of it, but ONLY
# when both of these hold:
#   1. The `pgvector` Python package is importable. It's a new dependency
#      (added to pyproject.toml alongside this change) that may not be
#      installed yet in an existing environment, and this module must
#      keep importing cleanly either way -- every other model in this
#      file depends on importing successfully regardless of whether
#      pgvector's wheel has landed.
#   2. The configured database is Postgres. The local SQLite dev DB's
#      `memories` table genuinely has no `embedding_vector` column (it is
#      never added by `_ensure_sqlite_memory_columns`, intentionally --
#      SQLite dev stays on the embedding_json/in-process-cosine fallback
#      path). If this column were declared unconditionally and pgvector
#      happened to be installed, `SELECT * FROM memories` issued by the
#      ORM for an ordinary query would ask SQLite for a column that does
#      not exist on disk and raise OperationalError on EVERY Memory
#      query. Gating on the dialect, decided once at import time from the
#      same Settings the rest of the app uses, avoids that trap.
try:
    from pgvector.sqlalchemy import Vector as _PgVector
except ImportError:  # pgvector not installed yet -- see core/config.require_pgvector
    _PgVector = None  # type: ignore[assignment,misc]

_memory_table_is_postgres = not get_settings().database_url.startswith("sqlite")


def uuid_str() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(40), default="google", nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailLoginCode(Base, TimestampMixin):
    __tablename__ = "email_login_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), default="login", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(120), default="New thought", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False, index=True)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str | None] = mapped_column(String(40))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    profile_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    preferred_review_time: Mapped[str | None] = mapped_column(String(40))
    recall_frequency: Mapped[str | None] = mapped_column(String(40))
    answer_style: Mapped[str | None] = mapped_column(String(40))
    evidence_strictness: Mapped[str] = mapped_column(String(40), default="balanced", nullable=False)
    challenge_style: Mapped[str] = mapped_column(String(40), default="balanced", nullable=False)
    memory_density: Mapped[str | None] = mapped_column(String(40))
    notification_preference: Mapped[str | None] = mapped_column(String(80))
    topics_of_interest: Mapped[list[str] | None] = mapped_column(JSON)
    source_preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    updated_from_message_id: Mapped[str | None] = mapped_column(ForeignKey("chat_messages.id"), index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    original_url: Mapped[str | None] = mapped_column(Text)
    resolved_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(255))
    publisher: Mapped[str | None] = mapped_column(String(255))
    captured_snapshot_uri: Mapped[str | None] = mapped_column(Text)
    raw_text_uri: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    extracted_text_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # LLM-written, organized markdown write-up of this source, produced
    # once by extraction (CaptureExtraction.source_overview_markdown) and
    # shown to the user as the "Original" tab's content instead of
    # `raw_text` -- a raw video transcript or article dump is often
    # unpunctuated / badly organized to actually read. `raw_text` is left
    # completely untouched: it's still the only thing extraction/chunking,
    # the content-hash dedup check, and re-extraction ever read from. Null
    # until extraction completes (e.g. the synchronous reference-only stub
    # before its background enrichment job runs -- see
    # capture_service._is_reference_placeholder_source), in which case API
    # consumers fall back to raw_text (see api/v1/sources.py).
    summary_markdown: Mapped[str | None] = mapped_column(Text)

    captures: Mapped[list[Capture]] = relationship(back_populates="source")
    memories: Mapped[list[Memory]] = relationship(back_populates="source")


class Capture(Base, TimestampMixin):
    __tablename__ = "captures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    user_note: Mapped[str | None] = mapped_column(Text)
    user_intent_text: Mapped[str | None] = mapped_column(Text)
    inferred_intents: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))

    source: Mapped[Source] = relationship(back_populates="captures")
    memories: Mapped[list[Memory]] = relationship(back_populates="capture")


class ProcessingJob(Base, TimestampMixin):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    job_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(80), default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    capture_id: Mapped[str | None] = mapped_column(ForeignKey("captures.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), index=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message_safe: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    capture_id: Mapped[str] = mapped_column(ForeignKey("captures.id"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(40), nullable=False)
    epistemic_label: Mapped[str | None] = mapped_column(String(80))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    confidence_reason: Mapped[str | None] = mapped_column(Text)
    source_strength: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    importance_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    decay_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False, index=True)
    embedding_json: Mapped[list[float] | None] = mapped_column(JSON)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recall_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Set only when extraction detected that this memory is one item of an
    # explicit enumerated list named by its source (e.g. "13 Businesses for
    # the Age of AI" -> 13 items). list_group_id ties every memory from the
    # same detected list together (shared across a Source, and across
    # chunks for a long document); list_position is this item's 1-based
    # position; list_total is how many items the source itself claims the
    # list has. All three are null for a memory that isn't part of a
    # detected list. This lets a caller answer "did I get all of them" and
    # "how many more are there" without re-reading the source, which was
    # previously impossible to represent at all — see extraction_service's
    # list-detection prompt rules and capture_service._create_memories.
    list_group_id: Mapped[str | None] = mapped_column(String(80), index=True)
    list_position: Mapped[int | None] = mapped_column(Integer)
    list_total: Mapped[int | None] = mapped_column(Integer)

    if _PgVector is not None and _memory_table_is_postgres:
        # See the module-level comment above for why both conditions are
        # required. The column itself is still created/migrated
        # exclusively by db/vector.py's raw-SQL `ensure_postgres_vector_schema`
        # (Base.metadata.create_all only creates missing TABLES, never adds
        # columns to a table that already exists, so this declaration
        # never races with that function's ALTER TABLE). What this adds is
        # the ability to actually reference `Memory.embedding_vector` from
        # Python/ORM code (filters, selects) instead of only through
        # hand-written SQL strings.
        embedding_vector: Mapped[list[float] | None] = mapped_column(
            _PgVector(QWEN_EMBEDDING_DIMENSIONS), nullable=True
        )

    source: Mapped[Source] = relationship(back_populates="memories")
    capture: Mapped[Capture] = relationship(back_populates="memories")


class RecallReview(Base, TimestampMixin):
    __tablename__ = "recall_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False, index=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    self_rating: Mapped[int | None] = mapped_column(Integer)
    evaluation_score: Mapped[float] = mapped_column(Float, nullable=False)
    rating: Mapped[str] = mapped_column(String(30), nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    understanding_summary: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_gaps: Mapped[list[str] | None] = mapped_column(JSON)
    context_to_consider: Mapped[list[str] | None] = mapped_column(JSON)
    next_question: Mapped[str | None] = mapped_column(Text)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), index=True)
    memory_id: Mapped[str | None] = mapped_column(ForeignKey("memories.id"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="scheduled", nullable=False, index=True)
    save_as_memory: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)  # stored as int for SQLite compat
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class PushSubscription(Base, TimestampMixin):
    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False, index=True)
    user_agent: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class NotificationDelivery(Base, TimestampMixin):
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    event_key: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message_safe: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class ActionItem(Base, TimestampMixin):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    memory_id: Mapped[str | None] = mapped_column(ForeignKey("memories.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="planned", nullable=False, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_from: Mapped[str] = mapped_column(String(40), default="memory", nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class MemoryArchiveEvent(Base, TimestampMixin):
    __tablename__ = "memory_archive_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False, index=True)
    previous_status: Mapped[str] = mapped_column(String(40), nullable=False)
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(40), default="user", nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class MemoryPerspectiveNote(Base, TimestampMixin):
    __tablename__ = "memory_perspective_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False, index=True)
    perspective_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_query: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    surface_after_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    surfaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(40), default="system", nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class MemoryRelation(Base, TimestampMixin):
    __tablename__ = "memory_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False)
    target_memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    strength: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(40), default="system", nullable=False)
