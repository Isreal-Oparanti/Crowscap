from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import RecallEvaluation
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Memory, RecallReview, Source, utc_now
from app.schemas.recall import (
    RecallAnswerRequest,
    RecallAnswerResponse,
    RecallQuickAction,
    RecallQuickRequest,
    RecallQuickResponse,
    RecallRelationshipResponse,
)
from app.services.recall_service import _relationships_for_recall_memories

logger = get_logger("services.recall_evaluation")


class RecallEvaluationError(RuntimeError):
    """Raised when a recall answer cannot be evaluated safely."""


class RecallEvaluator(Protocol):
    def evaluate(
        self,
        *,
        memory: Memory,
        source: Source,
        relationships: list[RecallRelationshipResponse],
        answer: str,
    ) -> RecallEvaluation:
        pass


class QwenRecallEvaluator:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()
        self.settings = get_settings()

    def evaluate(
        self,
        *,
        memory: Memory,
        source: Source,
        relationships: list[RecallRelationshipResponse],
        answer: str,
    ) -> RecallEvaluation:
        payload = self.client.chat_json(
            system_prompt=RECALL_EVALUATION_SYSTEM_PROMPT,
            user_prompt=_build_recall_evaluation_prompt(
                memory=memory,
                source=source,
                relationships=relationships,
                answer=answer,
            ),
            model=self.settings.qwen_chat_model,
            temperature=0.1,
        )
        try:
            return RecallEvaluation.model_validate(payload)
        except ValidationError as exc:
            raise RecallEvaluationError(
                f"Recall evaluation failed schema validation: {exc}"
            ) from exc


def get_recall_evaluator() -> RecallEvaluator:
    return QwenRecallEvaluator()


def answer_recall(
    *,
    db: Session,
    memory_id: str,
    payload: RecallAnswerRequest,
    evaluator: RecallEvaluator,
    user_id: str | None = None,
) -> RecallAnswerResponse:
    logger.info(
        "\U0001f9e0 recall.answer.start memory_id=%s chars=%s self_rating=%s",
        memory_id,
        len(payload.answer),
        payload.self_rating,
    )
    query = (
        select(Memory, Source)
        .join(Source, Memory.source_id == Source.id)
        .where(Memory.id == memory_id)
    )
    if user_id is None:
        query = query.where(Memory.user_id.is_(None))
    else:
        query = query.where(Memory.user_id == user_id)

    row = db.execute(query).first()
    if row is None:
        raise LookupError("Memory not found.")
    memory, source = row

    relationship_map = _relationships_for_recall_memories(db=db, memories=[memory])
    relationships = relationship_map.get(memory.id, [])
    evaluation = evaluator.evaluate(
        memory=memory,
        source=source,
        relationships=relationships,
        answer=payload.answer,
    )

    combined_score = _combined_recall_score(
        evaluation_score=evaluation.score,
        self_rating=payload.self_rating,
    )
    new_review_count = memory.review_count + 1
    next_due_at = _next_review_at(
        score=combined_score,
        review_count=new_review_count,
    )
    now = utc_now()
    memory.last_reviewed_at = now
    memory.review_count = new_review_count
    memory.recall_score = combined_score
    memory.next_review_at = next_due_at

    review = RecallReview(
        user_id=user_id,
        memory_id=memory.id,
        answer_text=payload.answer,
        self_rating=payload.self_rating,
        evaluation_score=evaluation.score,
        rating=evaluation.rating,
        feedback=evaluation.feedback,
        understanding_summary=evaluation.understanding_summary,
        knowledge_gaps=evaluation.knowledge_gaps,
        context_to_consider=evaluation.context_to_consider,
        next_question=evaluation.next_question,
        next_review_at=next_due_at,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    logger.info(
        "\u2705 recall.answer.complete memory_id=%s review_id=%s score=%.3f next_due_at=%s",
        memory.id,
        review.id,
        combined_score,
        next_due_at.isoformat(),
    )
    return RecallAnswerResponse(
        review_id=review.id,
        memory_id=memory.id,
        feedback=evaluation.feedback,
        score=round(evaluation.score, 4),
        rating=evaluation.rating,
        understanding_summary=evaluation.understanding_summary,
        knowledge_gaps=evaluation.knowledge_gaps,
        context_to_consider=evaluation.context_to_consider,
        next_question=evaluation.next_question,
        next_due_at=next_due_at,
        review_count=memory.review_count,
        recall_score=round(memory.recall_score, 4),
    )


def quick_recall(
    *,
    db: Session,
    memory_id: str,
    payload: RecallQuickRequest,
    user_id: str | None = None,
) -> RecallQuickResponse:
    logger.info(
        "\u26a1 recall.quick.start memory_id=%s action=%s",
        memory_id,
        payload.action,
    )
    query = select(Memory).where(Memory.id == memory_id)
    if user_id is None:
        query = query.where(Memory.user_id.is_(None))
    else:
        query = query.where(Memory.user_id == user_id)

    memory = db.scalar(query)
    if memory is None:
        raise LookupError("Memory not found.")

    now = utc_now()
    if payload.action == "not_now":
        next_due_at = now + timedelta(days=1)
        memory.next_review_at = next_due_at
        db.commit()
        logger.info(
            "\u2705 recall.quick.deferred memory_id=%s next_due_at=%s",
            memory.id,
            next_due_at.isoformat(),
        )
        return RecallQuickResponse(
            memory_id=memory.id,
            action=payload.action,
            feedback="No problem. I moved this out of the way and will bring it back later.",
            next_due_at=next_due_at,
            review_count=memory.review_count,
            recall_score=round(memory.recall_score, 4),
        )

    score, rating, feedback, interval = _quick_action_outcome(payload.action)
    next_due_at = now + interval
    memory.last_reviewed_at = now
    memory.review_count += 1
    memory.recall_score = max(memory.recall_score, score)
    memory.next_review_at = next_due_at

    review = RecallReview(
        user_id=user_id,
        memory_id=memory.id,
        answer_text=f"[quick recall] {payload.action}",
        self_rating=None,
        evaluation_score=score,
        rating=rating,
        feedback=feedback,
        understanding_summary=(
            "The user gave a lightweight recall signal instead of writing a full "
            "reflection."
        ),
        knowledge_gaps=[],
        context_to_consider=[],
        next_question=None,
        next_review_at=next_due_at,
    )
    db.add(review)
    db.commit()

    logger.info(
        "\u2705 recall.quick.complete memory_id=%s action=%s score=%.3f next_due_at=%s",
        memory.id,
        payload.action,
        memory.recall_score,
        next_due_at.isoformat(),
    )
    return RecallQuickResponse(
        memory_id=memory.id,
        action=payload.action,
        feedback=feedback,
        next_due_at=next_due_at,
        review_count=memory.review_count,
        recall_score=round(memory.recall_score, 4),
    )


def _quick_action_outcome(
    action: RecallQuickAction,
) -> tuple[float, str, str, timedelta]:
    if action == "applied":
        return (
            0.9,
            "strong",
            "Good. I’ll treat this as used knowledge and bring it back less often.",
            timedelta(days=14),
        )
    return (
        0.72,
        "solid",
        "Got it. I’ll keep this alive, but I won’t make it feel like homework.",
        timedelta(days=3),
    )


def _combined_recall_score(*, evaluation_score: float, self_rating: int | None) -> float:
    if self_rating is None:
        return round(evaluation_score, 4)
    self_score = (self_rating - 1) / 3
    return round((evaluation_score * 0.8) + (self_score * 0.2), 4)


def _next_review_at(*, score: float, review_count: int) -> datetime:
    if score < 0.35:
        interval = timedelta(hours=8)
    elif score < 0.55:
        interval = timedelta(days=1)
    elif score < 0.72:
        interval = timedelta(days=3)
    elif score < 0.88:
        interval = timedelta(days=7 * min(review_count, 2))
    else:
        interval = timedelta(days=14 * min(review_count, 2))
    return utc_now() + interval


def _build_recall_evaluation_prompt(
    *,
    memory: Memory,
    source: Source,
    relationships: list[RecallRelationshipResponse],
    answer: str,
) -> str:
    relation_text = "\n".join(
        (
            f"- {relationship.relationship_type} ({relationship.strength}): "
            f"{relationship.related_memory_content}. "
            f"{relationship.explanation or ''}"
        )
        for relationship in relationships
    ) or "No related memories."
    return f"""Evaluate the user's recall and help deepen understanding.

Return JSON:
{{
  "score": 0.0 to 1.0,
  "rating": "needs_work" | "partial" | "solid" | "strong",
  "feedback": "specific and encouraging feedback on the answer",
  "understanding_summary": "a concise synthesis of the important idea and why it matters",
  "knowledge_gaps": ["what the answer missed or what remains unsupported"],
  "context_to_consider": ["conditions, assumptions, evidence needs, or boundaries"],
  "next_question": "one question that makes the user think more deeply, or null"
}}

Evaluation rules:
- Reward retrieval and explanation in the user's own words, not exact wording.
- Evaluate against the saved memory and its related context.
- Do not treat the saved memory as automatically true.
- Use epistemic label, confidence, and source strength to point out when an idea is advice, opinion, weakly evidenced, or context-dependent.
- knowledge_gaps should identify what the user did not yet explain or verify.
- context_to_consider should help prevent familiarity from becoming false mastery.
- The understanding summary should connect the idea to its practical importance without becoming a generic textbook summary.
- Keep feedback useful and direct, not school-like or patronizing.

Saved memory:
{memory.content}

Memory metadata:
type={memory.memory_type}
epistemic_label={memory.epistemic_label}
confidence={memory.confidence}
confidence_reason={memory.confidence_reason}
source_strength={memory.source_strength}
source_title={source.title or 'Untitled source'}

Related memories and tensions:
{relation_text}

User answer:
{answer}
"""


RECALL_EVALUATION_SYSTEM_PROMPT = """You are Crowscap's recall evaluator.
Return only valid JSON. Diagnose understanding, missing context, and evidence gaps without pretending a saved claim is objective truth."""
