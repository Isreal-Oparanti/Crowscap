from __future__ import annotations

import json
from typing import Protocol

from pydantic import ValidationError

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import CaptureExtraction
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("services.extraction")


class ExtractionError(RuntimeError):
    """Raised when captured content cannot be converted into memory atoms."""


class MemoryExtractor(Protocol):
    def extract_text(
        self,
        *,
        text: str,
        intent_text: str | None = None,
        user_note: str | None = None,
    ) -> CaptureExtraction:
        pass


class QwenMemoryExtractor:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()
        self.settings = get_settings()

    def extract_text(
        self,
        *,
        text: str,
        intent_text: str | None = None,
        user_note: str | None = None,
    ) -> CaptureExtraction:
        logger.info(
            "\U0001f9ea extraction.start input_type=text chars=%s intent_present=%s note_present=%s",
            len(text),
            bool(intent_text),
            bool(user_note),
        )
        payload = self.client.chat_json(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=build_extraction_prompt(
                text=text,
                intent_text=intent_text,
                user_note=user_note,
            ),
            model=self.settings.qwen_extraction_model,
            temperature=0.0,
        )

        extraction = self._validate_or_repair(payload)

        logger.info(
            "\u2705 extraction.validated memories=%s intents=%s title=%s",
            len(extraction.memories),
            list(extraction.inferred_intents),
            extraction.source_title,
        )
        return extraction

    def _validate_or_repair(self, payload: dict) -> CaptureExtraction:
        validation_error: ValidationError
        try:
            return CaptureExtraction.model_validate(payload)
        except ValidationError as exc:
            validation_error = exc
            logger.warning(
                "\u26a0\ufe0f extraction.validation_repair.start errors=%s",
                validation_error.error_count(),
            )

        repaired_payload = self.client.chat_json(
            system_prompt=EXTRACTION_REPAIR_SYSTEM_PROMPT,
            user_prompt=build_extraction_repair_prompt(
                payload=payload,
                validation_error=validation_error,
            ),
            model=self.settings.qwen_fast_model,
            temperature=0.0,
            timeout_seconds=20.0,
            max_retries=1,  # allow one retry on transient network errors
        )
        try:
            repaired = CaptureExtraction.model_validate(repaired_payload)
        except ValidationError as second_error:
            logger.exception(
                "\u274c extraction.validation_repair.failed errors=%s",
                second_error.error_count(),
            )
            raise ExtractionError(
                "Crowscap could not structure this source reliably. Please try again."
            ) from second_error

        logger.info("\u2705 extraction.validation_repair.complete")
        return repaired


def get_memory_extractor() -> MemoryExtractor:
    return QwenMemoryExtractor()


EXTRACTION_SYSTEM_PROMPT = """You are Crowscap's memory extraction agent.

Return only valid JSON.
Base every memory on the captured text and the user's stated intent.
Do not invent facts that are not present in the captured text.
Do not call something true just because the source sounds confident.
Prefer small, atomic memory objects over long summaries.
Each memory must be understandable without reading the original source.
If the user is saving something to watch/read later, create an intention memory.
If the captured text contains conflicting claims, preserve both as separate memories and add a question memory that names the tension.
Confidence means confidence that the memory is supported by the captured text, not confidence that it is objectively true.
Source strength means evidence quality. Unsupported advice should not be "strong" only because it is stated clearly.
Keep memory_type and epistemic_label separate. "intention" is a memory_type; an intention's epistemic_label should usually be "personal_reflection".
"""


EXTRACTION_REPAIR_SYSTEM_PROMPT = """You repair Crowscap structured extraction JSON.
Return only valid JSON matching the supplied schema.
Preserve the original meaning and memories.
Correct field placement, label taxonomy, missing required fields, and length violations.
Do not add new factual claims."""


def build_extraction_prompt(
    *,
    text: str,
    intent_text: str | None = None,
    user_note: str | None = None,
) -> str:
    return f"""Extract structured memory atoms from the captured text.

The response must be JSON with this exact shape:
{{
  "source_title": "short title or null",
  "inferred_intents": ["learned" | "remember" | "watch_later" | "read_later" | "verify" | "apply" | "reference" | "inspiration" | "disagree" | "question" | "compare"],
  "memories": [
    {{
      "memory_type": "claim" | "principle" | "definition" | "example" | "warning" | "action" | "question" | "quote" | "reference" | "intention",
      "epistemic_label": "factual_claim" | "opinion" | "advice" | "anecdote" | "prediction" | "framework" | "personal_reflection" | "unresolved" | "source_summary",
      "content": "one atomic memory",
      "summary": "optional short summary or null",
      "confidence": "low" | "medium" | "high" | "unknown",
      "confidence_reason": "why this confidence is appropriate from the source text",
      "source_strength": "weak" | "moderate" | "strong" | "unknown"
    }}
  ]
}}

Rules:
- Return the smallest useful number of memories, usually 1 to 8 for short text.
- Split only when the text contains distinct ideas, actions, examples, questions, or intentions.
- Each memory must pass the isolation test: it should make sense without reading the original source.
- Use "intention" when the user has not consumed the source yet.
- Use "compare" in inferred_intents when the user wants to compare this capture with older memories.
- Use "action" only when the text or user intent implies something to do.
- Use "question" for unresolved things the user should inspect.
- If two ideas in the same capture conflict, preserve both and add a question memory about the tension.
- Use low or unknown confidence for unsupported advice/opinion.
- Use "strong" source_strength only for official, cited, data-backed, or clearly evidenced material.
- Use "moderate" or "weak" source_strength for standalone advice, opinions, or anecdotes.
- Do not include Markdown outside the JSON.

User intent text:
{intent_text or "None"}

User note:
{user_note or "None"}

Captured text:
```text
{text}
```
"""


def build_extraction_repair_prompt(
    *,
    payload: dict,
    validation_error: ValidationError,
) -> str:
    return f"""Repair this extraction payload so it matches the schema exactly.

Important distinctions:
- memory_type may be: claim, principle, definition, example, warning, action, question, quote, reference, intention.
- epistemic_label may be: factual_claim, opinion, advice, anecdote, prediction, framework, personal_reflection, unresolved, source_summary.
- "intention" is never an epistemic_label. For an intention memory, use personal_reflection unless source_summary is more appropriate.
- Keep all memories grounded in the existing payload. Do not invent new content.

Validation errors:
{json.dumps(validation_error.errors(include_url=False), ensure_ascii=True)}

Payload:
{json.dumps(payload, ensure_ascii=True)}
"""
