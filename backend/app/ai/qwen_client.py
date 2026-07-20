from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ai.qwen")

QWEN_EMBEDDING_BATCH_SIZE = 10


class QwenClientError(RuntimeError):
    """Raised when Qwen Cloud cannot be called safely."""


class QwenClient:
    """Small wrapper around Qwen Cloud's OpenAI-compatible API.

    The underlying openai.OpenAI instance (and its httpx connection pool) is
    constructed lazily on first use and then cached for the lifetime of this
    QwenClient instance. This avoids re-creating the HTTP client on every call.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None  # lazy-initialized by _build_client()

    def _build_client(self):
        if self._client is not None:
            return self._client

        if not self.settings.has_qwen_key:
            logger.warning("\u26a0\ufe0f qwen.key_missing env=DASHSCOPE_API_KEY")
            raise QwenClientError("DASHSCOPE_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise QwenClientError("The openai package is not installed.") from exc

        self._client = OpenAI(
            api_key=self.settings.dashscope_api_key_value,
            base_url=self.settings.qwen_base_url,
            timeout=60.0,
            max_retries=2,
        )
        return self._client

    def chat_once(self, prompt: str, *, model: str | None = None) -> str:
        client = self._build_client()
        selected_model = model or self.settings.qwen_fast_model

        try:
            completion = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a concise smoke-test responder for Crowscap.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            raise self._provider_error("chat", selected_model, exc) from exc

        content = completion.choices[0].message.content
        if not content:
            logger.error("\u274c qwen.response_empty mode=chat model=%s", selected_model)
            raise QwenClientError("Qwen Cloud returned an empty response.")

        logger.info("\u2705 qwen.response_ok mode=chat model=%s chars=%s", selected_model, len(content))
        return content.strip()

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        """Call Qwen with JSON mode and parse the response into a dict.

        Qwen's structured output mode guarantees valid JSON mode, but our
        business schema is still validated separately with Pydantic.
        """
        client = self._build_client()
        selected_model = model or self.settings.qwen_fast_model

        logger.info(
            "\U0001f916 qwen.request mode=json model=%s prompt_chars=%s",
            selected_model,
            len(system_prompt) + len(user_prompt),
        )
        request_client = client
        if timeout_seconds is not None or max_retries is not None:
            request_client = client.with_options(
                timeout=timeout_seconds,
                max_retries=max_retries,
            )

        try:
            completion = request_client.chat.completions.create(
                model=selected_model,
                messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        except Exception as exc:
            raise self._provider_error("json", selected_model, exc) from exc

        content = completion.choices[0].message.content
        if not content:
            logger.error("\u274c qwen.response_empty mode=json model=%s", selected_model)
            raise QwenClientError("Qwen Cloud returned an empty JSON response.")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.exception("\u274c qwen.invalid_json mode=json model=%s", selected_model)
            raise QwenClientError("Qwen Cloud returned invalid JSON.") from exc

        if not isinstance(parsed, dict):
            logger.error("\u274c qwen.json_not_object mode=json model=%s", selected_model)
            raise QwenClientError("Qwen Cloud returned JSON that is not an object.")

        logger.info(
            "\u2705 qwen.response_ok mode=json model=%s chars=%s keys=%s",
            selected_model,
            len(content),
            sorted(parsed.keys()),
        )
        return parsed

    def embed_texts(
        self,
        texts: Sequence[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        client = self._build_client()
        selected_model = model or self.settings.qwen_embedding_model
        text_list = list(texts)
        batch_count = (len(text_list) + QWEN_EMBEDDING_BATCH_SIZE - 1) // QWEN_EMBEDDING_BATCH_SIZE
        embeddings: list[list[float]] = []

        logger.info(
            "\U0001f9ec qwen.request mode=embedding model=%s items=%s batches=%s max_batch=%s",
            selected_model,
            len(text_list),
            batch_count,
            QWEN_EMBEDDING_BATCH_SIZE,
        )

        for batch_index, start in enumerate(
            range(0, len(text_list), QWEN_EMBEDDING_BATCH_SIZE),
            start=1,
        ):
            batch = text_list[start : start + QWEN_EMBEDDING_BATCH_SIZE]
            logger.info(
                "\U0001f9ec qwen.embedding_batch.start model=%s batch=%s/%s items=%s",
                selected_model,
                batch_index,
                batch_count,
                len(batch),
            )
            try:
                response = client.embeddings.create(
                    model=selected_model,
                    input=batch,
                )
            except Exception as exc:
                raise self._provider_error("embedding", selected_model, exc) from exc

            ordered = sorted(response.data, key=lambda item: item.index)
            batch_embeddings = [list(item.embedding) for item in ordered]

            if len(batch_embeddings) != len(batch):
                logger.error(
                    "\u274c qwen.embedding_count_mismatch batch=%s/%s expected=%s actual=%s",
                    batch_index,
                    batch_count,
                    len(batch),
                    len(batch_embeddings),
                )
                raise QwenClientError("Qwen Cloud returned the wrong number of embeddings.")

            embeddings.extend(batch_embeddings)
            logger.info(
                "\u2705 qwen.embedding_batch.ok model=%s batch=%s/%s items=%s",
                selected_model,
                batch_index,
                batch_count,
                len(batch_embeddings),
            )

        if len(embeddings) != len(text_list):
            logger.error(
                "\u274c qwen.embedding_count_mismatch expected=%s actual=%s",
                len(text_list),
                len(embeddings),
            )
            raise QwenClientError("Qwen Cloud returned the wrong number of embeddings.")

        dimensions = len(embeddings[0]) if embeddings else 0
        logger.info(
            "\u2705 qwen.response_ok mode=embedding model=%s items=%s batches=%s dimensions=%s",
            selected_model,
            len(embeddings),
            batch_count,
            dimensions,
        )
        return embeddings

    def _provider_error(self, mode: str, model: str, exc: Exception) -> QwenClientError:
        error_type = exc.__class__.__name__
        logger.exception(
            "\u274c qwen.request_failed mode=%s model=%s error_type=%s",
            mode,
            model,
            error_type,
        )

        if error_type in {"APIConnectionError", "ConnectError", "APITimeoutError", "TimeoutException"}:
            return QwenClientError(
                "Could not reach Qwen Cloud. Check internet/DNS, the QWEN_BASE_URL, and try again."
            )

        if error_type == "RateLimitError":
            return QwenClientError("Qwen Cloud rate limit or quota was reached.")

        if error_type == "AuthenticationError":
            return QwenClientError("Qwen Cloud authentication failed. Check DASHSCOPE_API_KEY.")

        if error_type == "PermissionDeniedError":
            return QwenClientError("Qwen Cloud denied access to this model or workspace.")

        if error_type == "BadRequestError" and mode == "embedding":
            return QwenClientError(
                "Qwen Cloud rejected the embedding request. Check embedding input size and model support."
            )

        if error_type == "BadRequestError":
            return QwenClientError("Qwen Cloud rejected the request. Check model and JSON mode support.")

        return QwenClientError(f"Qwen Cloud request failed: {error_type}.")
