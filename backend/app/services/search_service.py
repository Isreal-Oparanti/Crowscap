from __future__ import annotations

import math
import time

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Memory, Source
from app.db.vector import QWEN_EMBEDDING_DIMENSIONS, format_pgvector, is_postgres_bind
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.embedding_service import MemoryEmbedder

logger = get_logger("services.search")
QUERY_EMBEDDING_CACHE_MAX = 256
_QUERY_EMBEDDING_CACHE: dict[tuple[str, str], list[float]] = {}


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
    query_embedding = _embed_query(embedder=embedder, query=payload.query)
    embedding_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "\U0001f9ec search.query_embedded dimensions=%s latency_ms=%.1f",
        len(query_embedding),
        embedding_ms,
    )

    postgres_response = _search_memories_with_pgvector(
        db=db,
        payload=payload,
        query_embedding=query_embedding,
        user_id=user_id,
    )
    if postgres_response is not None:
        return postgres_response

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
                source_type=source.source_type,
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


def _search_memories_with_pgvector(
    *,
    db: Session,
    payload: SearchRequest,
    query_embedding: list[float],
    user_id: str | None,
) -> SearchResponse | None:
    if not is_postgres_bind(db.get_bind()):
        return None
    if len(query_embedding) != QWEN_EMBEDDING_DIMENSIONS:
        logger.warning(
            "⚠️ search.pgvector_skipped reason=dimension_mismatch expected=%s actual=%s",
            QWEN_EMBEDDING_DIMENSIONS,
            len(query_embedding),
        )
        return None

    where_parts = []
    params: dict[str, object] = {
        "query_vector": format_pgvector(query_embedding),
        "min_score": payload.min_score,
        "limit": payload.limit,
    }
    if user_id is None:
        where_parts.append("m.user_id IS NULL")
    else:
        where_parts.append("m.user_id = :user_id")
        params["user_id"] = user_id
    if not payload.include_archived:
        where_parts.append("m.status = 'active'")

    where_sql = " AND ".join(where_parts) if where_parts else "TRUE"

    try:
        candidate_count = int(
            db.execute(
                text(f"SELECT COUNT(*) FROM memories m WHERE {where_sql}"),
                params,
            ).scalar_one()
        )
        embedded_candidate_count = int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM memories m "
                    f"WHERE {where_sql} AND m.embedding_vector IS NOT NULL"
                ),
                params,
            ).scalar_one()
        )
        rows = db.execute(
            text(
                "SELECT "
                "m.id AS memory_id, "
                "m.source_id AS source_id, "
                "s.source_type AS source_type, "
                "s.title AS source_title, "
                "m.memory_type AS memory_type, "
                "m.epistemic_label AS epistemic_label, "
                "m.content AS content, "
                "m.summary AS summary, "
                "m.confidence AS confidence, "
                "m.confidence_reason AS confidence_reason, "
                "m.source_strength AS source_strength, "
                "1 - (m.embedding_vector <=> CAST(:query_vector AS vector)) AS similarity_score "
                "FROM memories m "
                "JOIN sources s ON m.source_id = s.id "
                f"WHERE {where_sql} "
                "AND m.embedding_vector IS NOT NULL "
                "AND (1 - (m.embedding_vector <=> CAST(:query_vector AS vector))) >= :min_score "
                "ORDER BY m.embedding_vector <=> CAST(:query_vector AS vector) "
                "LIMIT :limit"
            ),
            params,
        ).mappings()
    except SQLAlchemyError as exc:
        logger.warning(
            "⚠️ search.pgvector_failed reason=%s fallback=embedding_json",
            str(exc).replace("\n", " ")[:500],
        )
        return None

    results = [
        SearchResult(
            memory_id=str(row["memory_id"]),
            source_id=str(row["source_id"]),
            source_type=str(row["source_type"]),
            source_title=row["source_title"],
            memory_type=row["memory_type"],
            epistemic_label=row["epistemic_label"],
            content=row["content"],
            summary=row["summary"],
            confidence=row["confidence"],
            confidence_reason=row["confidence_reason"],
            source_strength=row["source_strength"],
            similarity_score=round(float(row["similarity_score"]), 6),
            embedding_dimensions=QWEN_EMBEDDING_DIMENSIONS,
        )
        for row in rows
    ]

    top_scores = [
        {
            "score": result.similarity_score,
            "memory_id": result.memory_id,
            "type": result.memory_type,
        }
        for result in results[:5]
    ]
    logger.info("\U0001f4ca search.pgvector_top_scores scores=%s", top_scores)
    logger.info(
        "\u2705 search.pgvector_complete candidates=%s embedded_candidates=%s returned=%s threshold=%s",
        candidate_count,
        embedded_candidate_count,
        len(results),
        payload.min_score,
    )

    return SearchResponse(
        query=payload.query,
        min_score=payload.min_score,
        candidate_count=candidate_count,
        embedded_candidate_count=embedded_candidate_count,
        returned_count=len(results),
        top_score=results[0].similarity_score if results else None,
        results=results,
    )


def _embed_query(*, embedder: MemoryEmbedder, query: str) -> list[float]:
    cache_key = (embedder.__class__.__name__, query.strip().lower())
    cached = _QUERY_EMBEDDING_CACHE.get(cache_key)
    if cached is not None:
        logger.info("♻️ search.query_embedding_cache_hit query_chars=%s", len(query))
        return cached

    embedding = embedder.embed_texts([query])[0]
    if len(_QUERY_EMBEDDING_CACHE) >= QUERY_EMBEDDING_CACHE_MAX:
        _QUERY_EMBEDDING_CACHE.pop(next(iter(_QUERY_EMBEDDING_CACHE)))
    _QUERY_EMBEDDING_CACHE[cache_key] = embedding
    return embedding


def _load_searchable_memories(
    *,
    db: Session,
    include_archived: bool,
    user_id: str | None,
) -> list[tuple[Memory, Source]]:
    """Load memories for in-process cosine similarity fallback (SQLite only).

    Capped at 1000 rows to prevent loading an unbounded result set into Python
    memory. At scale, the pgvector path takes over and this function is never
    reached.
    """
    SQLITE_FALLBACK_LIMIT = 1000
    query = (
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .limit(SQLITE_FALLBACK_LIMIT)
    )

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
