from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
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


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    original_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(255))
    publisher: Mapped[str | None] = mapped_column(String(255))
    captured_snapshot_uri: Mapped[str | None] = mapped_column(Text)
    raw_text_uri: Mapped[str | None] = mapped_column(Text)
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

    source: Mapped[Source] = relationship(back_populates="memories")
    capture: Mapped[Capture] = relationship(back_populates="memories")


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
