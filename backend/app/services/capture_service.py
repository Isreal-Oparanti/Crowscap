from __future__ import annotations

import hashlib
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.ai.structured_outputs import CaptureExtraction
from app.core.logging import get_logger
from app.db.models import Capture, Memory, MemoryRelation, Source
from app.schemas.capture import MemoryCardResponse, MemoryRelationshipResponse, TextCaptureRequest, TextCaptureResponse
from app.services.embedding_service import EmbeddingError, MemoryEmbedder
from app.services.extraction_service import MemoryExtractor
from app.services.relationship_service import MemoryRelationDetector, RelationshipDetectionError

logger = get_logger("services.capture")


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
    content_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()

    existing_source = _find_existing_text_source(
        db=db,
        content_hash=content_hash,
        user_id=user_id,
    )
    if existing_source is not None and existing_source.memories:
        latest_capture = _latest_capture_for_source(existing_source)
        if latest_capture is not None:
            _backfill_missing_embeddings(
                db=db,
                memories=list(existing_source.memories),
                embedder=embedder,
            )
            logger.info(
                "\u267b\ufe0f capture.text.duplicate_reused source_id=%s capture_id=%s memories=%s",
                existing_source.id,
                latest_capture.id,
                len(existing_source.memories),
            )
            return _build_text_capture_response(
                capture=latest_capture,
                source=existing_source,
                memories=list(existing_source.memories),
                relationships=_relationships_for_memories(db=db, memories=list(existing_source.memories)),
            )

    extraction = extractor.extract_text(
        text=payload.content,
        intent_text=payload.intent_text,
        user_note=payload.user_note,
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
        source_type="text",
        title=payload.source_title or extraction.source_title,
        extracted_text_hash=content_hash,
        metadata_json={
            "input_kind": "text_capture",
            "content_length": len(payload.content),
        },
    )
    db.add(source)
    db.flush()

    capture = Capture(
        user_id=user_id,
        source_id=source.id,
        user_note=payload.user_note,
        user_intent_text=payload.intent_text,
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

    relationships = _detect_relationships(
        db=db,
        memories=memories,
        detector=relation_detector,
        user_id=user_id,
    )
    db.commit()
    logger.info(
        "\U0001f4be capture.text.saved source_id=%s capture_id=%s memories=%s relationships=%s",
        source.id,
        capture.id,
        len(memories),
        len(relationships),
    )

    return _build_text_capture_response(
        capture=capture,
        source=source,
        memories=memories,
        relationships=relationships,
    )


def _find_existing_text_source(
    *,
    db: Session,
    content_hash: str,
    user_id: str | None,
) -> Source | None:
    query = (
        select(Source)
        .where(Source.source_type == "text")
        .where(Source.extracted_text_hash == content_hash)
        .where(Source.user_id.is_(None) if user_id is None else Source.user_id == user_id)
        .order_by(Source.created_at.desc())
    )
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

    db.commit()
    logger.info("\u2705 capture.text.embedding_backfill.complete memories=%s", len(missing))


def _detect_relationships(
    *,
    db: Session,
    memories: list[Memory],
    detector: MemoryRelationDetector,
    user_id: str | None,
) -> list[MemoryRelation]:
    try:
        return detector.detect_for_memories(db=db, new_memories=memories, user_id=user_id)
    except (QwenClientError, RelationshipDetectionError) as exc:
        logger.warning("\u26a0\ufe0f capture.text.relationships_skipped reason=%s", exc)
        return []


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
        )
        db.add(memory)
        memories.append(memory)

    db.flush()
    return memories


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
        status=capture.status,
        inferred_intents=list(capture.inferred_intents or []),
        memories=[
            MemoryCardResponse(
                id=memory.id,
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
