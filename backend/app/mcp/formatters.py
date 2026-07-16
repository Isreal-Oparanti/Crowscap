from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def dump_model(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def compact_search_result(result: BaseModel) -> dict[str, Any]:
    payload = dump_model(result)
    return {
        "memory_id": payload["memory_id"],
        "source_id": payload["source_id"],
        "source_type": payload["source_type"],
        "source_title": payload["source_title"],
        "memory_type": payload["memory_type"],
        "epistemic_label": payload["epistemic_label"],
        "content": payload["content"],
        "summary": payload["summary"],
        "confidence": payload["confidence"],
        "source_strength": payload["source_strength"],
        "similarity_score": payload["similarity_score"],
    }


def compact_relationship(relationship: BaseModel) -> dict[str, Any]:
    payload = dump_model(relationship)
    return {
        "related_memory_id": payload["related_memory_id"],
        "relationship_type": payload["relationship_type"],
        "strength": payload["strength"],
        "explanation": payload["explanation"],
        "direction": payload["direction"],
    }


def compact_due_memory(memory: BaseModel) -> dict[str, Any]:
    payload = dump_model(memory)
    return {
        "memory_id": payload["memory_id"],
        "source_id": payload["source_id"],
        "source_title": payload["source_title"],
        "memory_type": payload["memory_type"],
        "epistemic_label": payload["epistemic_label"],
        "content": payload["content"],
        "summary": payload["summary"],
        "confidence": payload["confidence"],
        "source_strength": payload["source_strength"],
        "next_review_at": payload["next_review_at"],
        "last_reviewed_at": payload["last_reviewed_at"],
        "review_count": payload["review_count"],
        "recall_score": payload["recall_score"],
        "overdue_seconds": payload["overdue_seconds"],
        "recall_prompt": payload["recall_prompt"],
        "epistemic_caution": payload["epistemic_caution"],
        "relationships": [
            compact_relationship(relationship) for relationship in memory.relationships
        ],
    }


def compact_reminder(reminder: BaseModel) -> dict[str, Any]:
    payload = dump_model(reminder)
    return {
        "reminder_id": payload["reminder_id"],
        "content": payload["content"],
        "due_at": payload["due_at"],
        "overdue_seconds": payload["overdue_seconds"],
        "save_as_memory": payload["save_as_memory"],
        "memory_id": payload["memory_id"],
        "status": payload["status"],
    }
