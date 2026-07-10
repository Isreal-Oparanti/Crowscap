from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


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


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(120), default="New thought", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)

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
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    embedding_json: Mapped[list[float] | None] = mapped_column(JSON)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recall_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

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
