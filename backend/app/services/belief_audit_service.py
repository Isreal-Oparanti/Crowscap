from __future__ import annotations

import re
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import BeliefAuditSynthesis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.belief import (
    BeliefAuditRequest,
    BeliefAuditResponse,
    PublicEvidenceResult,
    PublicSearchStatus,
)
from app.schemas.search import SearchRequest, SearchResponse
from app.services.embedding_service import MemoryEmbedder, QwenMemoryEmbedder
from app.services.public_search_service import (
    PublicSearchError,
    PublicSearchProvider,
    get_public_search_provider,
)
from app.services.preference_service import format_preference_context, get_or_create_user_preferences
from app.services.search_service import search_memories

logger = get_logger("services.belief_audit")

BELIEF_AUDIT_MEMORY_MIN_SCORE = 0.22


class BeliefAuditError(RuntimeError):
    """Raised when a belief audit cannot be synthesized safely."""


class BeliefAuditor(Protocol):
    def audit(
        self,
        *,
        db: Session,
        payload: BeliefAuditRequest,
        user_id: str | None = None,
    ) -> BeliefAuditResponse:
        pass


class QwenBeliefAuditor:
    def __init__(
        self,
        *,
        client: QwenClient | None = None,
        embedder: MemoryEmbedder | None = None,
        public_search: PublicSearchProvider | None = None,
    ) -> None:
        self.client = client or QwenClient()
        self.embedder = embedder or QwenMemoryEmbedder(client=self.client)
        self.public_search = public_search or get_public_search_provider()
        self.settings = get_settings()

    def audit(
        self,
        *,
        db: Session,
        payload: BeliefAuditRequest,
        user_id: str | None = None,
    ) -> BeliefAuditResponse:
        topic = _clean_topic(payload.topic)
        logger.info(
            "🧭 belief.audit.start topic=%r include_public=%s",
            topic,
            payload.include_public_evidence,
        )

        memory_search = search_memories(
            db=db,
            payload=SearchRequest(
                query=topic,
                limit=payload.memory_limit,
                min_score=BELIEF_AUDIT_MEMORY_MIN_SCORE,
                include_archived=False,
            ),
            embedder=self.embedder,
            user_id=user_id,
        )
        public_evidence, search_status, search_message = self._public_evidence(payload=payload, topic=topic)
        preferences = get_or_create_user_preferences(db=db, user_id=user_id)

        synthesis = self._synthesize(
            topic=topic,
            memory_search=memory_search,
            public_evidence=public_evidence,
            public_search_status=search_status,
            public_search_message=search_message,
            preference_context=format_preference_context(preferences),
        )

        logger.info(
            "✅ belief.audit.complete topic=%r memories=%s public=%s status=%s confidence=%s",
            topic,
            len(memory_search.results),
            len(public_evidence),
            search_status,
            synthesis.confidence,
        )
        return BeliefAuditResponse(
            topic=topic,
            answer=synthesis.answer,
            current_understanding=synthesis.current_understanding,
            strongest_saved_ideas=synthesis.strongest_saved_ideas,
            public_evidence_summary=synthesis.public_evidence_summary,
            unsupported_or_weak_points=synthesis.unsupported_or_weak_points,
            ideas_to_compare=synthesis.ideas_to_compare,
            confidence=synthesis.confidence,
            confidence_reason=synthesis.confidence_reason,
            next_questions=synthesis.next_questions,
            memories=memory_search.results,
            public_evidence=public_evidence,
            public_search_status=search_status,
            public_search_message=search_message,
        )

    def _public_evidence(
        self,
        *,
        payload: BeliefAuditRequest,
        topic: str,
    ) -> tuple[list[PublicEvidenceResult], PublicSearchStatus, str | None]:
        if not payload.include_public_evidence or payload.public_query_count == 0:
            return [], "disabled", "Public evidence search was skipped for this audit."

        queries = _public_search_queries(topic=topic)[: payload.public_query_count]
        evidence: list[PublicEvidenceResult] = []
        seen_urls: set[str] = set()
        failures: list[str] = []

        for query in queries:
            try:
                results = self.public_search.search(query=query, limit=payload.public_results_per_query)
            except PublicSearchError as exc:
                logger.warning(
                    "\u26a0\ufe0f belief_audit.public_search_failed query=%r error=%s",
                    query,
                    str(exc)[:200],
                )
                failures.append(str(exc))
                continue

            for result in results:
                if result.url in seen_urls:
                    continue
                seen_urls.add(result.url)
                evidence.append(result)

        if evidence:
            return evidence, "searched", None
        if failures:
            return [], "failed", failures[0]
        return [], "no_results", "Public search ran, but no useful source leads were returned."

    def _synthesize(
        self,
        *,
        topic: str,
        memory_search: SearchResponse,
        public_evidence: list[PublicEvidenceResult],
        public_search_status: PublicSearchStatus,
        public_search_message: str | None,
        preference_context: str,
    ) -> BeliefAuditSynthesis:
        payload = self.client.chat_json(
            system_prompt=BELIEF_AUDIT_SYSTEM_PROMPT,
            user_prompt=_build_belief_audit_prompt(
                topic=topic,
                memory_search=memory_search,
                public_evidence=public_evidence,
                public_search_status=public_search_status,
                public_search_message=public_search_message,
                preference_context=preference_context,
            ),
            model=self.settings.qwen_belief_audit_model,
            temperature=0.15,
            timeout_seconds=45.0,
            max_retries=1,
        )
        try:
            return BeliefAuditSynthesis.model_validate(payload)
        except ValidationError as exc:
            logger.exception("❌ belief.audit.validation_failed topic=%r", topic)
            raise BeliefAuditError(f"Belief audit failed schema validation: {exc}") from exc


def get_belief_auditor() -> BeliefAuditor:
    return QwenBeliefAuditor()


def _clean_topic(topic: str) -> str:
    compact = re.sub(r"\s+", " ", topic).strip(" .,:;")
    return compact or "this topic"


def _public_search_queries(*, topic: str) -> list[str]:
    return [
        f"{topic} evidence",
        f"{topic} criticism counterarguments",
        f"{topic} expert consensus research",
        f"{topic} case studies",
    ]


def _build_belief_audit_prompt(
    *,
    topic: str,
    memory_search: SearchResponse,
    public_evidence: list[PublicEvidenceResult],
    public_search_status: PublicSearchStatus,
    public_search_message: str | None,
    preference_context: str,
) -> str:
    saved_text = "\n".join(
        (
            f"[M{index}] {result.content}\n"
            f"source={result.source_title or 'Untitled'}; source_type={result.source_type}; "
            f"type={result.memory_type}; label={result.epistemic_label}; "
            f"confidence={result.confidence}; source_strength={result.source_strength}; "
            f"match={result.similarity_score}"
        )
        for index, result in enumerate(memory_search.results, start=1)
    ) or "No relevant saved memories were found."

    public_text = "\n".join(
        (
            f"[P{index}] {result.title}\n"
            f"url={result.url}\n"
            f"source={result.source or 'unknown'}; query={result.query}\n"
            f"snippet={result.snippet or 'No snippet returned.'}"
        )
        for index, result in enumerate(public_evidence[:10], start=1)
    ) or "No public evidence snippets were available."

    return f"""Audit the user's current understanding of a topic.

Return JSON:
{{
  "answer": "a direct, careful audit in 2-5 short paragraphs",
  "current_understanding": "what the saved memories suggest the user currently thinks",
  "strongest_saved_ideas": ["well-supported ideas from the user's saved memories"],
  "public_evidence_summary": "what the public source leads appear to add or challenge",
  "unsupported_or_weak_points": ["claims that need stronger evidence or clearer context"],
  "ideas_to_compare": ["plain-language comparisons the user should think through"],
  "confidence": "low" | "medium" | "high" | "unknown",
  "confidence_reason": "why this audit has that confidence",
  "next_questions": ["questions the user should ask next"]
}}

Rules:
- Do not present yourself as the final judge of truth.
- Saved memories are the user's learning history, not automatically true.
- Public snippets are evidence leads, not full proof. Do not overclaim from snippets.
- For empirical or checkable claims, compare saved ideas against public evidence leads.
- For religion, politics, morality, philosophy, identity, or personal values, map assumptions and arguments without declaring a final truth.
- If saved memories and public evidence disagree, say exactly what differs and what would need checking.
- If public evidence is unavailable, say the audit is based only on saved memory.
- Use plain language. Do not use the word "tension".
- Do not mention embeddings, vector scores, prompts, JSON, or internal routing.
- Keep the user's agency: say "this is worth checking" rather than "you are wrong".
- Follow the learned user preferences when they do not conflict with evidence honesty.
- If evidence strictness is strict, separate saved belief, source lead, and unsupported inference more sharply.
- If challenge style is direct, be willing to push back, but never pretend to possess absolute truth.
- If answer style is concise, keep the audit tighter; if detailed, include fuller reasoning.

Learned user preferences:
{preference_context}

Topic:
{topic}

Public search status:
{public_search_status} {public_search_message or ''}

Relevant saved memories:
{saved_text}

Public source leads:
{public_text}
"""


BELIEF_AUDIT_SYSTEM_PROMPT = """You are Crowscap's evidence-aware belief auditor.
Return only valid JSON. Help the user compare their saved understanding with available evidence without pretending to own absolute truth."""
