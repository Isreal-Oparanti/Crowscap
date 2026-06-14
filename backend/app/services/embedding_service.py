from __future__ import annotations

from typing import Protocol

from app.ai.qwen_client import QwenClient
from app.core.logging import get_logger

logger = get_logger("services.embedding")


class EmbeddingError(RuntimeError):
    """Raised when memory content cannot be embedded."""


class MemoryEmbedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        pass


class QwenMemoryEmbedder:
    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        logger.info("\U0001f9ec embedding.start memories=%s", len(texts))
        embeddings = self.client.embed_texts(texts)

        if len(embeddings) != len(texts):
            raise EmbeddingError("Embedding count did not match memory count.")

        if any(not embedding for embedding in embeddings):
            raise EmbeddingError("Qwen returned an empty embedding vector.")

        dimensions = len(embeddings[0]) if embeddings else 0
        logger.info("\u2705 embedding.complete memories=%s dimensions=%s", len(texts), dimensions)
        return embeddings


def get_memory_embedder() -> MemoryEmbedder:
    return QwenMemoryEmbedder()
