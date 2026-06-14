from __future__ import annotations

import math
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Memory, Source
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.embedding_service import MemoryEmbedder

logger = get_logger("services.search")


def search_memories(
    *,
    db: Session,
    payload: SearchRequest,
    embedder: MemoryEmbedder,
    user_id: str | None = None,
) -> SearchResponse:
    logger.info(
        "\U0001f50d search.start query_chars=%s limit=%s min_score=%s",
        len(payload.query),
        payload.limit,
        payload.min_score,
    )

    started_at = time.perf_counter()
    query_embedding = embedder.embed_texts([payload.query])[0]
    embedding_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "\U0001f9ec search.query_embedded dimensions=%s latency_ms=%.1f",
        len(query_embedding),
        embedding_ms,
    )

    rows = _load_searchable_memories(
        db=db,
        include_archived=payload.include_archived,
        user_id=user_id,
    )

    all_scored: list[SearchResult] = []
    for memory, source in rows:
        if not memory.embedding_json:
            continue

        score = cosine_similarity(query_embedding, memory.embedding_json)
        all_scored.append(
            SearchResult(
                memory_id=memory.id,
                source_id=source.id,
                source_title=source.title,
                memory_type=memory.memory_type,
                epistemic_label=memory.epistemic_label,
                content=memory.content,
                summary=memory.summary,
                confidence=memory.confidence,
                confidence_reason=memory.confidence_reason,
                source_strength=memory.source_strength,
                similarity_score=round(score, 6),
                embedding_dimensions=len(memory.embedding_json),
            )
        )

    all_scored.sort(key=lambda result: result.similarity_score, reverse=True)
    top_scores = [
        {
            "score": result.similarity_score,
            "memory_id": result.memory_id,
            "type": result.memory_type,
        }
        for result in all_scored[:5]
    ]
    logger.info("\U0001f4ca search.top_scores scores=%s", top_scores)

    filtered = [result for result in all_scored if result.similarity_score >= payload.min_score]
    results = filtered[: payload.limit]

    logger.info(
        "\u2705 search.complete candidates=%s embedded_candidates=%s returned=%s threshold=%s",
        len(rows),
        len(all_scored),
        len(results),
        payload.min_score,
    )
    return SearchResponse(
        query=payload.query,
        min_score=payload.min_score,
        candidate_count=len(rows),
        embedded_candidate_count=len(all_scored),
        returned_count=len(results),
        top_score=all_scored[0].similarity_score if all_scored else None,
        results=results,
    )


def _load_searchable_memories(
    *,
    db: Session,
    include_archived: bool,
    user_id: str | None,
) -> list[tuple[Memory, Source]]:
    query = select(Memory, Source).join(Source, Memory.source_id == Source.id)

    if user_id is None:
        query = query.where(Memory.user_id.is_(None))
    else:
        query = query.where(Memory.user_id == user_id)

    if not include_archived:
        query = query.where(Memory.status == "active")

    return list(db.execute(query).all())


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return -1.0

    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0

    return dot / (left_norm * right_norm)
