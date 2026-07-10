from types import SimpleNamespace

from app.ai.qwen_client import QwenClient


class FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, *, model: str, input: list[str]):
        self.calls.append(input)
        batch_number = len(self.calls)
        data = [
            SimpleNamespace(index=index, embedding=[float(batch_number), float(index)])
            for index, _text in enumerate(input)
        ]
        return SimpleNamespace(data=list(reversed(data)))


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()


def test_embed_texts_splits_requests_into_qwen_safe_batches(monkeypatch) -> None:
    fake_client = FakeOpenAIClient()
    client = QwenClient()
    monkeypatch.setattr(client, "_build_client", lambda: fake_client)

    embeddings = client.embed_texts(
        [f"memory {index}" for index in range(12)],
        model="text-embedding-v4",
    )

    assert [len(call) for call in fake_client.embeddings.calls] == [10, 2]
    assert len(embeddings) == 12
    assert embeddings[0] == [1.0, 0.0]
    assert embeddings[9] == [1.0, 9.0]
    assert embeddings[10] == [2.0, 0.0]
    assert embeddings[11] == [2.0, 1.0]
