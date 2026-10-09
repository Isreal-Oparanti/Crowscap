from __future__ import annotations

import json
from typing import Protocol

from pydantic import ValidationError

from app.ai.qwen_client import QwenClient
from app.ai.structured_outputs import (
    MAX_MEMORIES_PER_EXTRACTION,
    CaptureExtraction,
    ExtractedMemoryAtom,
)
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
            model=(
                self.settings.qwen_fast_model
                if len(text) < 20000
                else self.settings.qwen_extraction_model
            ),
            temperature=0.0,
            timeout_seconds=150.0,
            max_retries=1,
        )

        extraction = self._validate_or_repair(payload)

        logger.info(
            "\u2705 extraction.validated memories=%s intents=%s title=%s",
            len(extraction.memories),
            list(extraction.inferred_intents),
            extraction.source_title,
        )
        return extraction

    @staticmethod
    def _sanitize_extraction_payload(payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload
        sanitized = dict(payload)

        if "source_title" in sanitized and sanitized["source_title"]:
            sanitized["source_title"] = str(sanitized["source_title"]).strip()[:200]
        else:
            sanitized["source_title"] = None

        if sanitized.get("source_overview_markdown"):
            sanitized["source_overview_markdown"] = str(
                sanitized["source_overview_markdown"]
            ).strip()[:6000]
        else:
            sanitized["source_overview_markdown"] = None

        raw_intents = sanitized.get("inferred_intents")
        if isinstance(raw_intents, list):
            sanitized["inferred_intents"] = [str(item) for item in raw_intents if item]
        else:
            sanitized["inferred_intents"] = ["learned"]

        raw_memories = sanitized.get("memories")
        if isinstance(raw_memories, list):
            cleaned_memories = []
            for mem in raw_memories:
                if not isinstance(mem, dict):
                    continue
                m = dict(mem)
                content = str(m.get("content", "")).strip()
                if len(content) < 8:
                    continue
                m["content"] = content[:1200]

                if m.get("summary"):
                    m["summary"] = str(m["summary"]).strip()[:300]
                else:
                    m["summary"] = None

                conf_reason = str(m.get("confidence_reason", "Extracted directly from source.")).strip()
                if len(conf_reason) < 8:
                    conf_reason = f"{conf_reason} (extracted from source)"
                m["confidence_reason"] = conf_reason[:500]

                # Pass list tags through untouched; ExtractedMemoryAtom's own
                # validators reconcile an inconsistent position/total pair.
                cleaned_memories.append(m)
            if len(cleaned_memories) > MAX_MEMORIES_PER_EXTRACTION:
                logger.warning(
                    "⚠️ extraction.sanitize.truncated raw_count=%s cap=%s",
                    len(cleaned_memories),
                    MAX_MEMORIES_PER_EXTRACTION,
                )
            sanitized["memories"] = cleaned_memories[:MAX_MEMORIES_PER_EXTRACTION]

        return sanitized


    def _validate_or_repair(self, payload: dict) -> CaptureExtraction:
        try:
            return CaptureExtraction.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "⚠️ extraction.validation_error errors=%s",
                exc.error_count(),
            )

        # 1. Attempt instantaneous Python-level normalization and repair (0ms vs 20s LLM call)
        sanitized = self._sanitize_extraction_payload(payload)
        try:
            repaired = CaptureExtraction.model_validate(sanitized)
            logger.info("⚡ extraction.sanitized_in_python memories=%s", len(repaired.memories))
            return repaired
        except ValidationError as sanitize_exc:
            logger.warning("⚠️ extraction.sanitization_incomplete errors=%s", sanitize_exc.error_count())

        # 2. Salvage all valid memory atoms directly without waiting for a 20s LLM call
        valid_memories = []
        for item in (sanitized.get("memories") or payload.get("memories") or []):
            try:
                valid_memories.append(ExtractedMemoryAtom.model_validate(item))
            except Exception:
                continue
        if valid_memories:
            logger.info("🛡️ extraction.salvaged valid_memories=%s", len(valid_memories))
            return CaptureExtraction(
                source_title=sanitized.get("source_title") or payload.get("source_title") or "Captured Document",
                inferred_intents=sanitized.get("inferred_intents") or ["learned"],
                source_overview_markdown=(
                    sanitized.get("source_overview_markdown") or payload.get("source_overview_markdown")
                ),
                memories=valid_memories,
            )

        # 3. Only if Python salvage produces zero valid memories, fall back to LLM repair
        try:
            repaired_payload = self.client.chat_json(
                system_prompt=EXTRACTION_REPAIR_SYSTEM_PROMPT,
                user_prompt=build_extraction_repair_prompt(
                    payload=payload,
                    validation_error=exc,
                ),
                model=self.settings.qwen_fast_model,
                temperature=0.0,
                timeout_seconds=60.0,
                max_retries=1,
            )
            repaired = CaptureExtraction.model_validate(repaired_payload)
            logger.info("✅ extraction.validation_repair.complete")
            return repaired
        except Exception as repair_err:
            logger.warning("⚠️ extraction.validation_repair.fallback reason=%s", repair_err)
            raise ExtractionError(
                "Crowscap could not structure this source reliably. Please try again."
            ) from repair_err


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
Always write summaries, intentions, and memory content using 2nd person ("You intend to...", "You plan to...") or direct active voice. Never refer to the user in the 3rd person as "User" or "The user".

If the source itself names an explicit enumerated count (e.g. a title or heading like "13 Businesses for the Age of AI", "7 Habits of...", "Top 10 ..."), that count is a hard requirement, not a style choice:
- Extract exactly that many list-item memories, one atom per enumerated item, even if that is far more than you would normally return for content of this length.
- Tag every one of those atoms with the same "list_group_id" (invent a short stable slug from the source title), its own 1-based "list_position", and the full "list_total". Do not tag ordinary, non-list memories (an intention memory for the source as a whole, a question memory about a tension) with list fields.
- If the source text is cut short and you cannot see all of the named items, extract only the items actually present, still tag them with the true "list_total" from the title, and add one "question" memory noting that the capture appears to be missing items (name how many were visible vs. named).
- This list-item rule overrides the "usually 1 to 8" guidance below for that source; the two guidelines are not in tension because the "usually 1 to 8" case is for content that is NOT an explicit enumerated list.

You must also write "source_overview_markdown": one holistic, well-organized markdown write-up of the ENTIRE captured text, separate from the atomic memories. This is shown to the user as their record of what the source actually said, so it must be readable on its own without the memory cards:
- Use markdown headings (##), short paragraphs, and bullet lists to organize it by topic/section, not by copying the source's raw sentence order.
- Condense and clean up filler, false starts, and spoken-language artifacts (common in video transcripts) — this is a write-up for a reader, not a transcript dump.
- Do not drop content to make it short; cover everything the source actually said. Length should scale with how much real content there is.
- Stay strictly grounded in the captured text. Do not add claims, numbers, or examples that are not present in it.
- This is the one field in this response that SHOULD contain markdown syntax (the "no Markdown outside the JSON" rule below is about the overall response shape, i.e. don't wrap the JSON itself in a code fence or add prose before/after it — it does not apply to this field's own string value).
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
  "source_overview_markdown": "one organized markdown write-up of the whole source (see instructions above) or null if the text is too short/fragmentary to summarize meaningfully (under ~30 words)",
  "memories": [
    {{
      "memory_type": "claim" | "principle" | "definition" | "example" | "warning" | "action" | "question" | "quote" | "reference" | "intention",
      "epistemic_label": "factual_claim" | "opinion" | "advice" | "anecdote" | "prediction" | "framework" | "personal_reflection" | "unresolved" | "source_summary",
      "content": "one atomic memory",
      "summary": "optional short summary or null",
      "confidence": "low" | "medium" | "high" | "unknown",
      "confidence_reason": "why this confidence is appropriate from the source text",
      "source_strength": "weak" | "moderate" | "strong" | "unknown",
      "list_group_id": "short stable slug, or null when this memory is not part of a named enumerated list",
      "list_position": "1-based position in that list, or null",
      "list_total": "total number of items the source named, or null"
    }}
  ]
}}

Rules:
- Return the smallest useful number of memories, usually 1 to 8 for short text — UNLESS the source title or heading names an explicit enumerated count (see the list-extraction instructions above), in which case return exactly that many list-item memories plus any non-list memories (intentions, tension questions) the content separately calls for.
- Scale the number of memories with the amount of real content. Very short content (under 150 words, such as a short video transcript or a one-line note) almost always contains only 1 to 3 genuinely distinct ideas. Never split one idea into multiple near-duplicate memories to inflate the count. This does not apply when the source names an explicit list — a short transcript that is just a spoken list of 13 named items still yields 13 list-item memories.
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
- Only set list_group_id/list_position/list_total when the source itself names an explicit enumerated list (see above); leave all three null otherwise.
- Always produce "source_overview_markdown" unless the text is too short/fragmentary to summarize meaningfully.
- Do not include Markdown outside the JSON (the JSON response itself must not be wrapped in a code fence or preceded/followed by prose) — this does not restrict markdown syntax inside the "source_overview_markdown" string value itself, which should use it.

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
- Preserve "source_overview_markdown" exactly as given if present; do not drop it while repairing other fields.

Validation errors:
{json.dumps(validation_error.errors(include_url=False), ensure_ascii=True)}

Payload:
{json.dumps(payload, ensure_ascii=True)}
"""
