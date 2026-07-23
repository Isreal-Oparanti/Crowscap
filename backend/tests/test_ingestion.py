import json

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.structured_outputs import CaptureExtraction, ExtractedMemoryAtom
from app.db.base import Base
from app.db.models import Memory, Source
from app.schemas.capture import UrlCaptureRequest
from app.services.ingestion_service import (
    FetchedContent,
    IngestionError,
    _request_with_retries,
    _youtube_reference_metadata,
    clean_transcript,
    create_pdf_capture_from_bytes,
    create_url_capture,
    create_youtube_capture,
    extract_youtube_video_id,
    fetch_youtube_reference_metadata,
    unsupported_url_reason,
    validate_pdf_bytes,
    validate_public_url,
)


class FakeExtractor:
    def extract_text(
        self,
        *,
        text: str,
        intent_text: str | None = None,
        user_note: str | None = None,
    ) -> CaptureExtraction:
        return CaptureExtraction(
            source_title="Extracted source",
            inferred_intents=["learned"],
            memories=[
                ExtractedMemoryAtom(
                    memory_type="principle",
                    epistemic_label="advice",
                    content="Useful sources should become durable memory atoms.",
                    summary="Sources become memory atoms.",
                    confidence="high",
                    confidence_reason="The fake extractor always returns a supported atom.",
                    source_strength="moderate",
                )
            ],
        )


class FakeEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeRelationDetector:
    def detect_for_memories(
        self,
        *,
        db: Session,
        new_memories: list[Memory],
        user_id: str | None = None,
    ) -> list:
        return []


def build_db() -> tuple[sessionmaker[Session], Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session, testing_session()


def test_validate_public_url_rejects_localhost() -> None:
    with pytest.raises(IngestionError):
        validate_public_url("http://localhost:8000/internal")


def test_youtube_url_detection_supports_common_formats() -> None:
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert extract_youtube_video_id("https://youtu.be/abc123") == "abc123"
    assert extract_youtube_video_id("https://www.youtube.com/shorts/abc123") == "abc123"
    assert extract_youtube_video_id("https://m.youtube.com/shorts/abc123?si=share") == "abc123"


def test_youtube_reference_metadata_preserves_known_title() -> None:
    metadata = _youtube_reference_metadata(
        {
            "title": " 3 common YC interview mistakes ",
            "uploader": "Founder School",
            "duration": 58,
            "upload_date": "20260719",
            "view_count": 12000,
        },
        video_id="ythRYUxLEks",
    )

    assert metadata == {
        "input_kind": "youtube_reference",
        "video_id": "ythRYUxLEks",
        "source_type_hint": "youtube",
        "channel": "Founder School",
        "duration": 58,
        "publish_date": "20260719",
        "view_count": 12000,
        "title": "3 common YC interview mistakes",
    }


def test_youtube_oembed_metadata_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 200

        def json(self) -> dict:
            return {
                "title": "How to Apply And Succeed at Y Combinator | Startup School",
                "author_name": "Y Combinator",
                "author_url": "https://www.youtube.com/@ycombinator",
                "thumbnail_url": "https://i.ytimg.com/vi/B5tU2447OK8/hqdefault.jpg",
                "provider_name": "YouTube",
            }

    monkeypatch.setattr("app.services.ingestion_service.httpx.get", lambda *_, **__: FakeResponse())

    metadata = fetch_youtube_reference_metadata(
        url="https://youtu.be/B5tU2447OK8",
        video_id="B5tU2447OK8",
    )

    assert metadata["title"] == "How to Apply And Succeed at Y Combinator | Startup School"
    assert metadata["channel"] == "Y Combinator"
    assert metadata["metadata_providers"] == ["youtube_oembed"]


def test_youtube_capture_falls_back_to_metadata_when_transcript_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _testing_session, db = build_db()

    class BotBlockedYoutubeDL:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def extract_info(self, *_args, **_kwargs):
            raise RuntimeError("Sign in to confirm you're not a bot")

    monkeypatch.setattr("yt_dlp.YoutubeDL", BotBlockedYoutubeDL)
    monkeypatch.setattr(
        "app.services.ingestion_service.fetch_youtube_reference_metadata",
        lambda **_kwargs: {
            "title": "3 common YC interview mistakes",
            "channel": "Y Combinator",
            "thumbnail_url": "https://i.ytimg.com/vi/ythRYUxLEks/hq2.jpg",
        },
    )

    response = create_youtube_capture(
        db=db,
        url="https://www.youtube.com/watch?v=ythRYUxLEks",
        video_id="ythRYUxLEks",
        intent_text="will be useful during my YC application",
        user_note=None,
        extractor=FakeExtractor(),
        embedder=FakeEmbedder(),
        relation_detector=FakeRelationDetector(),
    )

    assert response.source_type == "youtube"
    assert response.source_title == "3 common YC interview mistakes"
    assert "3 common YC interview mistakes" in response.original_content
    assert "will be useful during my YC application" in response.original_content
    assert response.metadata_json is not None
    assert response.metadata_json["ingestion_mode"] == "metadata_only"
    assert response.metadata_json["transcript_status"] == "unavailable"
    db.close()


def test_whatsapp_invite_url_is_marked_unsupported() -> None:
    reason = unsupported_url_reason("https://chat.whatsapp.com/LK0yk9lerym0VmBi7C8EF7")

    assert reason is not None
    assert "WhatsApp group invite links" in reason


def test_public_url_network_failure_gets_clear_retryable_message() -> None:
    class FailingClient:
        calls = 0

        def request(self, method: str, url: str):
            self.calls += 1
            raise httpx.ConnectError("getaddrinfo failed")

    client = FailingClient()

    with pytest.raises(IngestionError) as error:
        _request_with_retries(client, "GET", "https://example.com/article")

    assert client.calls == 2
    assert "network/DNS issue" in str(error.value)
    assert "try again" in str(error.value).lower()


def test_clean_transcript_removes_timestamps_and_duplicates() -> None:
    raw = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello there
Hello there
00:00:02.000 --> 00:00:04.000
[Music]
Build useful things
"""
    assert clean_transcript(raw) == "Hello there Build useful things"


def test_clean_json3_transcript_removes_noise_markers() -> None:
    raw = {
        "events": [
            {"segs": [{"utf8": "[Music] "}, {"utf8": "Build useful things"}]},
            {"segs": [{"utf8": " [Applause]"}]},
        ]
    }

    assert clean_transcript(json.dumps(raw)) == "Build useful things"


def test_validate_pdf_bytes_rejects_non_pdf() -> None:
    with pytest.raises(IngestionError):
        validate_pdf_bytes(b"not a pdf" * 200)


def test_url_capture_uses_article_source_type(monkeypatch: pytest.MonkeyPatch) -> None:
    _testing_session, db = build_db()

    def fake_validate(url: str) -> str:
        return url

    def fake_fetch(url: str) -> FetchedContent:
        return FetchedContent(
            url="https://example.com/final",
            content_type="text/html",
            body=b"<html><body><article>Useful article text about memory systems.</article></body></html>",
        )

    def fake_extract(body: bytes, *, url: str) -> str:
        return "Useful article text about memory systems and durable recall."

    monkeypatch.setattr("app.services.ingestion_service.validate_public_url", fake_validate)
    monkeypatch.setattr("app.services.ingestion_service.fetch_public_url", fake_fetch)
    monkeypatch.setattr("app.services.ingestion_service.extract_article_text", fake_extract)

    response = create_url_capture(
        db=db,
        payload=UrlCaptureRequest(url="https://example.com/article"),
        extractor=FakeExtractor(),
        embedder=FakeEmbedder(),
        relation_detector=FakeRelationDetector(),
    )

    assert response.source_type == "article"
    assert response.memories[0].source_type == "article"
    assert response.original_content.startswith("Useful article")
    assert db.scalar(select(func.count(Source.id))) == 1
    db.close()


def test_pdf_capture_extracts_text_and_deduplicates() -> None:
    import fitz

    _testing_session, db = build_db()
    document = fitz.open()
    page = document.new_page()
    for index in range(4):
        page.insert_text(
            (72, 72 + index * 40),
            (
                "This is a text PDF about memory systems and recall. "
                "It contains enough real selectable text for Crowscap to process safely. "
                "The document explains how captured learning can become durable knowledge."
            ),
        )
    pdf_bytes = document.tobytes()
    document.close()

    first = create_pdf_capture_from_bytes(
        db=db,
        file_bytes=pdf_bytes,
        filename="memory.pdf",
        extractor=FakeExtractor(),
        embedder=FakeEmbedder(),
        relation_detector=FakeRelationDetector(),
    )
    second = create_pdf_capture_from_bytes(
        db=db,
        file_bytes=pdf_bytes,
        filename="memory.pdf",
        extractor=FakeExtractor(),
        embedder=FakeEmbedder(),
        relation_detector=FakeRelationDetector(),
    )

    assert first.source_type == "pdf"
    assert second.source_id == first.source_id
    assert db.scalar(select(func.count(Source.id))) == 1
    db.close()
