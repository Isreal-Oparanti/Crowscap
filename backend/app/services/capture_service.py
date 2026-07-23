from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.ai.structured_outputs import CaptureExtraction
from app.core.logging import get_logger
from app.db.models import Capture, Memory, MemoryRelation, Source, utc_now
from app.db.vector import update_memory_embedding_vector
from app.schemas.capture import (
    MemoryCardResponse,
    MemoryRelationshipResponse,
    TextCaptureRequest,
    TextCaptureResponse,
)
from app.services.embedding_service import EmbeddingError, MemoryEmbedder
from app.services.extraction_service import MemoryExtractor
from app.services.perspective_service import queue_perspective_notes_for_memories
from app.services.relationship_service import MemoryRelationDetector, RelationshipDetectionError
from app.services.safety_service import guard_capture_content

logger = get_logger("services.capture")

RELATIONSHIP_SCAN_COMPLETED_KEY = "relationship_scan_completed"
RELATIONSHIP_SCAN_CREATED_COUNT_KEY = "relationship_scan_created_count"


def create_text_capture(
    *,
    db: Session,
    payload: TextCaptureRequest,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_id: str | None = None,
) -> TextCaptureResponse:
    logger.info(
        "\U0001f4e5 capture.text.start chars=%s intent_present=%s note_present=%s",
        len(payload.content),
        bool(payload.intent_text),
        bool(payload.user_note),
    )
    return create_extracted_text_capture(
        db=db,
        source_type="text",
        raw_text=payload.content,
        title=payload.source_title,
        user_note=payload.user_note,
        intent_text=payload.intent_text,
        metadata_json={
            "input_kind": "text_capture",
            "content_length": len(payload.content),
        },
        extractor=extractor,
        embedder=embedder,
        relation_detector=relation_detector,
        user_id=user_id,
    )


def create_extracted_text_capture(
    *,
    db: Session,
    source_type: str,
    raw_text: str,
    title: str | None,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_note: str | None = None,
    intent_text: str | None = None,
    original_url: str | None = None,
    resolved_url: str | None = None,
    content_hash: str | None = None,
    metadata_json: dict | None = None,
    source_instruction: str | None = None,
    user_id: str | None = None,
) -> TextCaptureResponse:
    metadata = dict(metadata_json or {})
    safety_result = guard_capture_content(raw_text)
    if safety_result.redactions:
        raw_text = safety_result.safe_text
        metadata["safety_redactions"] = safety_result.redactions
        metadata["safety_notice"] = "Personal identifiers were removed before storage."
        logger.info(
            "\U0001f6e1\ufe0f capture.text.safety_redacted categories=%s",
            safety_result.redactions,
        )

    content_hash = content_hash or hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    existing_source = _find_existing_source(
        db=db,
        source_type=source_type,
        content_hash=content_hash,
        resolved_url=resolved_url,
        user_id=user_id,
    )
    if existing_source is not None and existing_source.memories:
        latest_capture = _latest_capture_for_source(existing_source)
        if latest_capture is not None:
            if not existing_source.raw_text:
                existing_source.raw_text = raw_text
                db.commit()
                logger.info(
                    "\U0001f527 capture.text.original_backfilled source_id=%s chars=%s",
                    existing_source.id,
                    len(raw_text),
                )
            memories = list(existing_source.memories)
            _backfill_missing_embeddings(
                db=db,
                memories=memories,
                embedder=embedder,
            )
            relationships = _backfill_missing_relationships(
                db=db,
                source=existing_source,
                memories=memories,
                detector=relation_detector,
                user_id=user_id,
            )
            perspective_notes = queue_perspective_notes_for_memories(
                db=db,
                memories=memories,
                user_id=user_id,
            )
            if perspective_notes:
                db.commit()
            logger.info(
                "\u267b\ufe0f capture.text.duplicate_reused source_id=%s capture_id=%s memories=%s relationships=%s perspective_notes=%s",
                existing_source.id,
                latest_capture.id,
                len(memories),
                len(relationships),
                len(perspective_notes),
            )
            return _build_text_capture_response(
                capture=latest_capture,
                source=existing_source,
                memories=memories,
                relationships=relationships,
            )

    extraction = _extract_from_raw_text(
        extractor=extractor,
        raw_text=raw_text,
        intent_text=intent_text,
        user_note=user_note,
        source_instruction=source_instruction,
    )
    logger.info(
        "\U0001f9e0 capture.text.extracted memories=%s intents=%s",
        len(extraction.memories),
        list(extraction.inferred_intents),
    )
    embeddings = embedder.embed_texts([atom.content for atom in extraction.memories])
    _validate_embeddings(embeddings, expected_count=len(extraction.memories))
    logger.info(
        "\U0001f9ec capture.text.embedded memories=%s dimensions=%s",
        len(embeddings),
        len(embeddings[0]) if embeddings else 0,
    )

    source = Source(
        user_id=user_id,
        source_type=source_type,
        original_url=original_url,
        resolved_url=resolved_url,
        title=title or extraction.source_title,
        raw_text=raw_text,
        extracted_text_hash=content_hash,
        metadata_json=metadata,
    )
    db.add(source)
    db.flush()

    capture = Capture(
        user_id=user_id,
        source_id=source.id,
        user_note=user_note,
        user_intent_text=intent_text,
        inferred_intents=list(extraction.inferred_intents),
        status="ready",
    )
    db.add(capture)
    db.flush()

    memories = _create_memories(
        db=db,
        extraction=extraction,
        source_id=source.id,
        capture_id=capture.id,
        user_id=user_id,
        embeddings=embeddings,
    )
    perspective_notes = queue_perspective_notes_for_memories(
        db=db,
        memories=memories,
        user_id=user_id,
    )

    relationships, relationship_scan_completed = _detect_relationships(
        db=db,
        memories=memories,
        detector=relation_detector,
        user_id=user_id,
    )
    if relationship_scan_completed:
        _mark_relationship_scan_completed(source=source, created_count=len(relationships))

    db.commit()
    logger.info(
        "\U0001f4be capture.text.saved source_id=%s capture_id=%s memories=%s relationships=%s perspective_notes=%s",
        source.id,
        capture.id,
        len(memories),
        len(relationships),
        len(perspective_notes),
    )

    return _build_text_capture_response(
        capture=capture,
        source=source,
        memories=memories,
        relationships=relationships,
    )


def _extract_from_raw_text(
    *,
    extractor: MemoryExtractor,
    raw_text: str,
    intent_text: str | None,
    user_note: str | None,
    source_instruction: str | None,
) -> CaptureExtraction:
    extraction_note = "\n".join(
        part for part in [source_instruction, user_note] if part
    ) or None
    words = raw_text.split()
    if len(words) <= 3_000:
        return extractor.extract_text(
            text=raw_text,
            intent_text=intent_text,
            user_note=extraction_note,
        )

    logger.info("\U0001f9e9 capture.chunking.start words=%s", len(words))
    chunks = _chunk_words(words, chunk_size=2_000, overlap=200)
    merged_intents: list[str] = []
    merged_memories = []
    seen_memory_content: set[str] = set()
    source_title: str | None = None

    for index, chunk in enumerate(chunks, start=1):
        chunk_note = "\n".join(
            part
            for part in [
                extraction_note,
                f"This is chunk {index} of {len(chunks)} from one source. Avoid duplicate memories.",
            ]
            if part
        )
        chunk_extraction = extractor.extract_text(
            text=chunk,
            intent_text=intent_text,
            user_note=chunk_note,
        )
        source_title = source_title or chunk_extraction.source_title
        for intent in chunk_extraction.inferred_intents:
            if intent not in merged_intents:
                merged_intents.append(intent)
        for memory in chunk_extraction.memories:
            normalized = " ".join(memory.content.lower().split())
            if normalized in seen_memory_content:
                continue
            seen_memory_content.add(normalized)
            merged_memories.append(memory)
            if len(merged_memories) >= 12:
                break
        if len(merged_memories) >= 12:
            break

    logger.info(
        "\u2705 capture.chunking.complete chunks=%s memories=%s",
        len(chunks),
        len(merged_memories),
    )
    return CaptureExtraction(
        source_title=source_title,
        inferred_intents=merged_intents[:5],
        memories=merged_memories,
    )


def _chunk_words(words: list[str], *, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _find_existing_source(
    *,
    db: Session,
    source_type: str,
    content_hash: str,
    resolved_url: str | None,
    user_id: str | None,
) -> Source | None:
    query = (
        select(Source)
        .where(Source.source_type == source_type)
        .where(Source.user_id.is_(None) if user_id is None else Source.user_id == user_id)
        .order_by(Source.created_at.desc())
    )
    if resolved_url:
        query = query.where(Source.resolved_url == resolved_url)
    else:
        query = query.where(Source.extracted_text_hash == content_hash)
    return db.scalars(query).first()


def _latest_capture_for_source(source: Source) -> Capture | None:
    captures = sorted(source.captures, key=lambda capture: capture.created_at, reverse=True)
    return captures[0] if captures else None


def _backfill_missing_embeddings(
    *,
    db: Session,
    memories: list[Memory],
    embedder: MemoryEmbedder,
) -> None:
    missing = [memory for memory in memories if not memory.embedding_json]
    if not missing:
        return

    logger.info("\U0001f527 capture.text.embedding_backfill.start memories=%s", len(missing))
    embeddings = embedder.embed_texts([memory.content for memory in missing])
    _validate_embeddings(embeddings, expected_count=len(missing))

    for memory, embedding in zip(missing, embeddings, strict=True):
        memory.embedding_json = embedding

    db.flush()
    vector_count = sum(
        1
        for memory in missing
        if update_memory_embedding_vector(
            db=db,
            memory_id=memory.id,
            embedding=memory.embedding_json,
        )
    )
    db.commit()
    logger.info(
        "\u2705 capture.text.embedding_backfill.complete memories=%s vectors=%s",
        len(missing),
        vector_count,
    )


def _backfill_missing_relationships(
    *,
    db: Session,
    source: Source,
    memories: list[Memory],
    detector: MemoryRelationDetector,
    user_id: str | None,
) -> list[MemoryRelation]:
    existing_relationships = _relationships_for_memories(db=db, memories=memories)
    if existing_relationships:
        return existing_relationships

    if _relationship_scan_completed(source):
        return []

    logger.info("\U0001f527 capture.text.relationship_backfill.start memories=%s", len(memories))
    new_relationships, relationship_scan_completed = _detect_relationships(
        db=db,
        memories=memories,
        detector=detector,
        user_id=user_id,
    )
    if relationship_scan_completed:
        _mark_relationship_scan_completed(source=source, created_count=len(new_relationships))
        db.commit()

    logger.info(
        "\u2705 capture.text.relationship_backfill.complete relationships=%s completed=%s",
        len(new_relationships),
        relationship_scan_completed,
    )
    return existing_relationships + new_relationships


def _detect_relationships(
    *,
    db: Session,
    memories: list[Memory],
    detector: MemoryRelationDetector,
    user_id: str | None,
) -> tuple[list[MemoryRelation], bool]:
    try:
        return detector.detect_for_memories(db=db, new_memories=memories, user_id=user_id), True
    except (QwenClientError, RelationshipDetectionError) as exc:
        logger.warning("\u26a0\ufe0f capture.text.relationships_skipped reason=%s", exc)
        return [], False


def _relationship_scan_completed(source: Source) -> bool:
    return bool((source.metadata_json or {}).get(RELATIONSHIP_SCAN_COMPLETED_KEY))


def _mark_relationship_scan_completed(*, source: Source, created_count: int) -> None:
    metadata = dict(source.metadata_json or {})
    metadata[RELATIONSHIP_SCAN_COMPLETED_KEY] = True
    metadata[RELATIONSHIP_SCAN_CREATED_COUNT_KEY] = created_count
    source.metadata_json = metadata


def _validate_embeddings(embeddings: list[list[float]], *, expected_count: int) -> None:
    if len(embeddings) != expected_count:
        raise EmbeddingError("Embedding count did not match memory count.")
    if any(not embedding for embedding in embeddings):
        raise EmbeddingError("Qwen returned an empty embedding vector.")


def _create_memories(
    *,
    db: Session,
    extraction: CaptureExtraction,
    source_id: str,
    capture_id: str,
    user_id: str | None,
    embeddings: list[list[float]],
) -> list[Memory]:
    memories: list[Memory] = []

    for atom, embedding in zip(extraction.memories, embeddings, strict=True):
        memory = Memory(
            user_id=user_id,
            source_id=source_id,
            capture_id=capture_id,
            memory_type=atom.memory_type,
            epistemic_label=atom.epistemic_label,
            content=atom.content,
            summary=atom.summary,
            confidence=atom.confidence,
            confidence_reason=atom.confidence_reason,
            source_strength=atom.source_strength,
            embedding_json=embedding,
            next_review_at=initial_next_review_at(memory_confidence=atom.confidence),
            review_count=0,
            recall_score=0.5,
        )
        db.add(memory)
        memories.append(memory)

    db.flush()
    vector_count = sum(
        1
        for memory in memories
        if update_memory_embedding_vector(
            db=db,
            memory_id=memory.id,
            embedding=memory.embedding_json,
        )
    )
    if vector_count:
        logger.info("\U0001f9ec capture.text.pgvector_written memories=%s", vector_count)
    return memories


def initial_next_review_at(*, memory_confidence: str) -> datetime:
    intervals = {
        "high": timedelta(hours=24),
        "medium": timedelta(hours=12),
        "low": timedelta(hours=6),
        "unknown": timedelta(hours=6),
    }
    return utc_now() + intervals.get(memory_confidence, timedelta(hours=6))


def _build_text_capture_response(
    *,
    capture: Capture,
    source: Source,
    memories: list[Memory],
    relationships: list[MemoryRelation] | None = None,
) -> TextCaptureResponse:
    relationships_by_memory: dict[str, list[MemoryRelationshipResponse]] = defaultdict(list)
    for relation in relationships or []:
        relationships_by_memory[relation.source_memory_id].append(
            MemoryRelationshipResponse(
                related_memory_id=relation.target_memory_id,
                relationship_type=relation.relation_type,
                strength=relation.strength,
                explanation=relation.explanation,
            )
        )

    return TextCaptureResponse(
        capture_id=capture.id,
        source_id=source.id,
        source_type=source.source_type,
        source_title=source.title,
        original_content=source.raw_text,
        status=capture.status,
        inferred_intents=list(capture.inferred_intents or []),
        metadata_json=source.metadata_json,
        memories=[
            MemoryCardResponse(
                id=memory.id,
                source_type=source.source_type,
                memory_type=memory.memory_type,
                epistemic_label=memory.epistemic_label,
                content=memory.content,
                summary=memory.summary,
                confidence=memory.confidence,
                confidence_reason=memory.confidence_reason,
                source_strength=memory.source_strength,
                embedding_dimensions=len(memory.embedding_json) if memory.embedding_json else None,
                relationships=relationships_by_memory[memory.id],
            )
            for memory in memories
        ],
    )


def _relationships_for_memories(*, db: Session, memories: list[Memory]) -> list[MemoryRelation]:
    memory_ids = [memory.id for memory in memories]
    if not memory_ids:
        return []

    query = select(MemoryRelation).where(MemoryRelation.source_memory_id.in_(memory_ids))
    return list(db.scalars(query).all())
