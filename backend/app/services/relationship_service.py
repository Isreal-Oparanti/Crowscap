from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import MemoryRelationshipAssessment, MemoryRelationshipBatch
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Memory, MemoryRelation, Source
from app.services.search_service import cosine_similarity

logger = get_logger("services.relationship")


class RelationshipDetectionError(RuntimeError):
    """Raised when memory relationships cannot be classified safely."""


class MemoryRelationDetector(Protocol):
    def detect_for_memories(
        self,
        *,
        db: Session,
        new_memories: list[Memory],
        user_id: str | None = None,
    ) -> list[MemoryRelation]:
        pass


@dataclass(frozen=True)
class RelationCandidate:
    memory: Memory
    source: Source
    similarity_score: float


@dataclass(frozen=True)
class RelationCheck:
    memory: Memory
    candidates: list[RelationCandidate]


RELATION_ELIGIBLE_MEMORY_TYPES = {"claim", "principle", "definition", "example", "warning", "action", "quote"}


class QwenMemoryRelationDetector:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()
        self.settings = get_settings()

    def detect_for_memories(
        self,
        *,
        db: Session,
        new_memories: list[Memory],
        user_id: str | None = None,
    ) -> list[MemoryRelation]:
        if not new_memories:
            return []

        eligible_memories = [
            memory for memory in new_memories if memory.memory_type in RELATION_ELIGIBLE_MEMORY_TYPES
        ]
        logger.info(
            "\U0001f9f2 relationship.scan.start memories=%s eligible=%s skipped_meta=%s threshold=%s limit=%s pair_limit=%s near_duplicate_max=%s",
            len(new_memories),
            len(eligible_memories),
            len(new_memories) - len(eligible_memories),
            self.settings.relationship_candidate_min_score,
            self.settings.relationship_candidate_limit,
            self.settings.relationship_pair_limit,
            self.settings.relationship_near_duplicate_max_score,
        )

        checks: list[RelationCheck] = []
        for memory in eligible_memories:
            candidates = self._find_candidates(db=db, memory=memory, user_id=user_id)
            if not candidates:
                logger.info("\U0001f9f2 relationship.scan.no_candidates memory_id=%s", memory.id)
                continue
            checks.append(RelationCheck(memory=memory, candidates=candidates))

        checks = self._cap_total_pairs(checks)
        if not checks:
            logger.info("\u2705 relationship.scan.complete created=0")
            return []

        assessments = self._classify_batch(checks=checks)
        candidates_by_memory = {
            check.memory.id: {candidate.memory.id: candidate for candidate in check.candidates}
            for check in checks
        }
        created: list[MemoryRelation] = []
        for assessment in assessments.relationships:
            if assessment.relationship_type == "unrelated":
                continue
            if assessment.strength in {"weak", "unknown"}:
                logger.info(
                    "\U0001f9f9 relationship.weak_skipped source_memory_id=%s related_memory_id=%s strength=%s",
                    assessment.source_memory_id,
                    assessment.related_memory_id,
                    assessment.strength,
                )
                continue

            candidate = candidates_by_memory.get(assessment.source_memory_id, {}).get(
                assessment.related_memory_id
            )
            if candidate is None:
                logger.warning(
                    "\u26a0\ufe0f relationship.unknown_candidate memory_id=%s related_memory_id=%s",
                    assessment.source_memory_id,
                    assessment.related_memory_id,
                )
                continue

            if not _assessment_is_grounded(
                assessment=assessment,
                source_memory=next(
                    check.memory
                    for check in checks
                    if check.memory.id == assessment.source_memory_id
                ),
                related_memory=candidate.memory,
            ):
                logger.warning(
                    "\u26a0\ufe0f relationship.ungrounded_skipped source_memory_id=%s related_memory_id=%s",
                    assessment.source_memory_id,
                    assessment.related_memory_id,
                )
                continue

            if _relation_exists(
                db=db,
                source_memory_id=assessment.source_memory_id,
                target_memory_id=candidate.memory.id,
            ):
                continue

            relation = MemoryRelation(
                user_id=user_id,
                source_memory_id=assessment.source_memory_id,
                target_memory_id=candidate.memory.id,
                relation_type=assessment.relationship_type,
                strength=assessment.strength,
                explanation=assessment.explanation,
                created_by="qwen",
            )
            db.add(relation)
            created.append(relation)

        db.flush()
        logger.info("\u2705 relationship.scan.complete created=%s", len(created))
        return created

    def _find_candidates(
        self,
        *,
        db: Session,
        memory: Memory,
        user_id: str | None,
    ) -> list[RelationCandidate]:
        if not memory.embedding_json:
            return []

        query = (
            select(Memory, Source)
            .join(Source, Memory.source_id == Source.id)
            .where(Memory.id != memory.id)
            .where(Memory.capture_id != memory.capture_id)
            .where(Memory.status == "active")
            .where(Memory.memory_type.in_(RELATION_ELIGIBLE_MEMORY_TYPES))
        )
        if user_id is None:
            query = query.where(Memory.user_id.is_(None))
        else:
            query = query.where(Memory.user_id == user_id)

        candidates: list[RelationCandidate] = []
        for candidate_memory, source in db.execute(query).all():
            if not candidate_memory.embedding_json:
                continue

            score = cosine_similarity(memory.embedding_json, candidate_memory.embedding_json)
            if score < self.settings.relationship_candidate_min_score:
                continue
            if score > self.settings.relationship_near_duplicate_max_score:
                logger.info(
                    "\u267b\ufe0f relationship.candidate_near_duplicate_skipped source_memory_id=%s target_memory_id=%s score=%.6f",
                    memory.id,
                    candidate_memory.id,
                    score,
                )
                continue

            candidates.append(
                RelationCandidate(
                    memory=candidate_memory,
                    source=source,
                    similarity_score=round(score, 6),
                )
            )

        candidates.sort(key=lambda candidate: candidate.similarity_score, reverse=True)
        top_candidates = candidates[: self.settings.relationship_candidate_limit]
        logger.info(
            "\U0001f4ca relationship.candidates memory_id=%s scores=%s",
            memory.id,
            [
                {
                    "score": candidate.similarity_score,
                    "memory_id": candidate.memory.id,
                    "type": candidate.memory.memory_type,
                }
                for candidate in top_candidates
            ],
        )
        return top_candidates

    def _cap_total_pairs(self, checks: list[RelationCheck]) -> list[RelationCheck]:
        pairs: list[tuple[Memory, RelationCandidate]] = []
        for check in checks:
            for candidate in check.candidates:
                pairs.append((check.memory, candidate))

        pairs.sort(key=lambda pair: pair[1].similarity_score, reverse=True)
        selected = pairs[: self.settings.relationship_pair_limit]
        selected_by_memory: dict[str, list[RelationCandidate]] = {}
        memory_by_id: dict[str, Memory] = {}

        for memory, candidate in selected:
            memory_by_id[memory.id] = memory
            selected_by_memory.setdefault(memory.id, []).append(candidate)

        logger.info(
            "\U0001f6a6 relationship.pairs_capped before=%s after=%s",
            len(pairs),
            len(selected),
        )
        return [
            RelationCheck(memory=memory_by_id[memory_id], candidates=candidates)
            for memory_id, candidates in selected_by_memory.items()
        ]

    def _classify_batch(
        self,
        *,
        checks: list[RelationCheck],
    ) -> MemoryRelationshipBatch:
        payload = self.client.chat_json(
            system_prompt=RELATIONSHIP_SYSTEM_PROMPT,
            user_prompt=build_relationship_prompt(checks=checks),
            model=self.settings.qwen_relationship_model,
            temperature=0.0,
            timeout_seconds=self.settings.relationship_timeout_seconds,
            max_retries=self.settings.relationship_max_retries,
        )
        try:
            return MemoryRelationshipBatch.model_validate(payload)
        except ValidationError as exc:
            logger.exception("\u274c relationship.validation_failed checks=%s", len(checks))
            raise RelationshipDetectionError(f"Qwen relationship detection failed validation: {exc}") from exc


def get_memory_relation_detector() -> MemoryRelationDetector:
    return QwenMemoryRelationDetector()


def _relation_exists(*, db: Session, source_memory_id: str, target_memory_id: str) -> bool:
    query = select(MemoryRelation.id).where(
        or_(
            (MemoryRelation.source_memory_id == source_memory_id)
            & (MemoryRelation.target_memory_id == target_memory_id),
            (MemoryRelation.source_memory_id == target_memory_id)
            & (MemoryRelation.target_memory_id == source_memory_id),
        )
    )
    return db.scalars(query).first() is not None


RELATIONSHIP_SYSTEM_PROMPT = """You are Crowscap's memory relationship classifier.

Return only valid JSON.
Classify how one newly captured memory relates to older memories.
The user may provide several new memories in one request. Classify only the candidate pairs listed.
Most topically similar memories are still unrelated. Your default decision is to omit the pair.
A meaningful relationship must concern the same underlying claim, mechanism, object, or real-world decision.
Shared generic words, both being products, or both mentioning technology are not meaningful relationships.
Different products or domains are unrelated unless both memories make comparable claims about the same decision.
Use "conflicts" only when both ideas address the same claim and cannot reasonably be true together.
Use "tension" only when both ideas could guide the same decision in different directions depending on context.
Use "confirms" when the older memory supports the new memory.
Use "extends" when the older memory adds detail, an example, or a next step.
Use "qualifies" when the older memory narrows, limits, or adds conditions to the new memory.
Never infer a product capability, cause, intention, or fact that is not explicitly stated in either memory.
For every returned relationship, quote a short exact phrase from each memory as evidence.
The explanation must be fully supported by those two exact phrases.
Write the explanation in plain language. Do not use taxonomy words such as "tension".
Do not overstate relationships. Omit any weak, merely topical, or uncertain connection.
Return only meaningful non-unrelated relationships. If no pair is meaningful, return {"relationships": []}.
"""


def build_relationship_prompt(*, checks: list[RelationCheck]) -> str:
    check_blocks = []
    for check in checks:
        candidate_lines = []
        for candidate in check.candidates:
            candidate_lines.append(
                f"""  - related_memory_id: {candidate.memory.id}
  similarity_score: {candidate.similarity_score}
  memory_type: {candidate.memory.memory_type}
  epistemic_label: {candidate.memory.epistemic_label}
  confidence: {candidate.memory.confidence}
  source_strength: {candidate.memory.source_strength}
  source_title: {candidate.source.title or "Untitled source"}
  content: {candidate.memory.content}"""
            )

        check_blocks.append(
            f"""New memory:
source_memory_id: {check.memory.id}
memory_type: {check.memory.memory_type}
epistemic_label: {check.memory.epistemic_label}
confidence: {check.memory.confidence}
source_strength: {check.memory.source_strength}
content: {check.memory.content}

Candidate memories:
{chr(10).join(candidate_lines)}"""
        )

    return f"""Classify the relationship between each new memory and each of its candidate memories.

The response must be JSON with this exact shape:
{{
  "relationships": [
    {{
      "source_memory_id": "new memory id",
      "related_memory_id": "candidate memory id",
      "relationship_type": "confirms" | "conflicts" | "tension" | "extends" | "qualifies",
      "strength": "moderate" | "strong",
      "evidence_from_source": "an exact phrase copied from the new memory",
      "evidence_from_related": "an exact phrase copied from the candidate memory",
      "explanation": "one sentence explaining the relationship"
    }}
  ]
}}

Rules:
- Return only meaningful relationship objects.
- Include both source_memory_id and related_memory_id exactly as provided.
- Do not create relationships for memories or candidates not listed.
- Omit a pair when the connection is merely topical or repetitive.
- Omit a pair when the memories concern different products, actors, mechanisms, or decisions.
- Evidence phrases must appear verbatim in their respective memory content.
- Never mention a capability or concept absent from both memory contents.
- Explain the connection conversationally without using the word "tension".

Checks:
{chr(10).join(check_blocks)}
"""


def _assessment_is_grounded(
    *,
    assessment: MemoryRelationshipAssessment,
    source_memory: Memory,
    related_memory: Memory,
) -> bool:
    return _contains_exact_evidence(
        content=source_memory.content,
        evidence=assessment.evidence_from_source,
    ) and _contains_exact_evidence(
        content=related_memory.content,
        evidence=assessment.evidence_from_related,
    )


def _contains_exact_evidence(*, content: str, evidence: str) -> bool:
    normalized_content = " ".join(content.casefold().split())
    normalized_evidence = " ".join(evidence.casefold().split())
    return normalized_evidence in normalized_content
