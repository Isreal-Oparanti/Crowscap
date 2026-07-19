from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.schemas.capture import UrlCaptureRequest, TextCaptureResponse
from app.services.capture_service import create_extracted_text_capture
from app.services.embedding_service import MemoryEmbedder
from app.services.extraction_service import MemoryExtractor
from app.services.relationship_service import MemoryRelationDetector

logger = get_logger("services.ingestion")

MAX_URL_LENGTH = 2048
MAX_FETCH_BYTES = 5 * 1024 * 1024
MAX_PDF_BYTES = 10 * 1024 * 1024
MIN_PDF_BYTES = 1024
MIN_EXTRACTED_CHARS = 100
MIN_TRANSCRIPT_WORDS = 100
MAX_TRANSCRIPT_WORDS = 15_000
USER_AGENT = "CrowscapBot/0.1 (+https://crowscap.local)"


class IngestionError(RuntimeError):
    """Raised when an external source cannot be safely ingested."""


@dataclass(frozen=True)
class FetchedContent:
    url: str
    content_type: str
    body: bytes


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"}:
            self._skip_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        stripped = data.strip()
        if stripped:
            self._parts.append(stripped)

    def text(self) -> str:
        return _normalize_text(" ".join(self._parts))


def create_url_capture(
    *,
    db: Session,
    payload: UrlCaptureRequest,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_id: str | None = None,
) -> TextCaptureResponse:
    logger.info("\U0001f517 capture.url.start url=%s", payload.url)
    validated_url = validate_public_url(payload.url)
    if reason := unsupported_url_reason(validated_url):
        raise IngestionError(reason)

    if video_id := extract_youtube_video_id(validated_url):
        return create_youtube_capture(
            db=db,
            url=f"https://www.youtube.com/watch?v={video_id}",
            video_id=video_id,
            intent_text=payload.intent_text,
            user_note=payload.user_note,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=user_id,
        )

    fetched = fetch_public_url(validated_url)
    if "application/pdf" in fetched.content_type or fetched.body[:5] == b"%PDF-":
        return create_pdf_capture_from_bytes(
            db=db,
            file_bytes=fetched.body,
            filename=fetched.url.rsplit("/", 1)[-1] or "source.pdf",
            original_url=validated_url,
            resolved_url=fetched.url,
            intent_text=payload.intent_text,
            user_note=payload.user_note,
            extractor=extractor,
            embedder=embedder,
            relation_detector=relation_detector,
            user_id=user_id,
        )

    if not _looks_like_html(fetched.content_type):
        raise IngestionError(
            "Crowscap can only process article pages, YouTube links, or PDFs from URLs right now."
        )

    article = extract_article_text(fetched.body, url=fetched.url)
    content_hash = hashlib.sha256(article.encode("utf-8")).hexdigest()
    return create_extracted_text_capture(
        db=db,
        source_type="article",
        raw_text=article,
        title=None,
        original_url=validated_url,
        resolved_url=fetched.url,
        content_hash=content_hash,
        intent_text=payload.intent_text,
        user_note=payload.user_note,
        metadata_json={
            "input_kind": "url_article",
            "content_length": len(article),
            "content_type": fetched.content_type,
        },
        source_instruction="This content came from a web article. Ignore navigation, ads, and boilerplate.",
        extractor=extractor,
        embedder=embedder,
        relation_detector=relation_detector,
        user_id=user_id,
    )


def create_youtube_capture(
    *,
    db: Session,
    url: str,
    video_id: str,
    intent_text: str | None,
    user_note: str | None,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    user_id: str | None = None,
) -> TextCaptureResponse:
    logger.info("\U0001f3a5 capture.youtube.start video_id=%s", video_id)
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise IngestionError("YouTube ingestion is not installed. Install yt-dlp.") from exc

    try:
        with YoutubeDL({"quiet": True, "skip_download": True, "nocheckcertificate": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        logger.warning(
            "\u26a0\ufe0f capture.youtube.failed video_id=%s error_type=%s",
            video_id,
            type(exc).__name__,
        )
        raise IngestionError(
            "Crowscap could not read this YouTube video. It may be private, unavailable, age-restricted, or missing readable captions."
        ) from exc

    if not isinstance(info, dict):
        raise IngestionError("Crowscap could not read this YouTube video metadata.")

    track = _choose_caption_track(info)
    if track is None:
        raise IngestionError(
            "This video does not have captions available. Crowscap cannot process videos without transcripts."
        )

    caption_text = _download_caption_text(track["url"])
    transcript = clean_transcript(caption_text)
    word_count = len(transcript.split())
    if word_count < MIN_TRANSCRIPT_WORDS:
        raise IngestionError("This video's transcript is too short to extract useful memories.")
    if word_count > MAX_TRANSCRIPT_WORDS:
        transcript = " ".join(transcript.split()[:MAX_TRANSCRIPT_WORDS])

    metadata = {
        "input_kind": "youtube",
        "video_id": video_id,
        "channel": info.get("uploader") or info.get("channel"),
        "duration": info.get("duration"),
        "publish_date": info.get("upload_date"),
        "view_count": info.get("view_count"),
        "caption_kind": track["kind"],
        "caption_language": track["language"],
        "content_length": len(transcript),
    }
    return create_extracted_text_capture(
        db=db,
        source_type="youtube",
        raw_text=transcript,
        title=info.get("title"),
        original_url=url,
        resolved_url=f"https://www.youtube.com/watch?v={video_id}",
        content_hash=video_id,
        intent_text=intent_text,
        user_note=user_note,
        metadata_json=metadata,
        source_instruction=(
            "This content came from a spoken video transcript. The speaker may repeat "
            "themselves or use filler language. Prioritize distinct ideas over every statement."
        ),
        extractor=extractor,
        embedder=embedder,
        relation_detector=relation_detector,
        user_id=user_id,
    )


def create_pdf_capture_from_bytes(
    *,
    db: Session,
    file_bytes: bytes,
    filename: str,
    extractor: MemoryExtractor,
    embedder: MemoryEmbedder,
    relation_detector: MemoryRelationDetector,
    intent_text: str | None = None,
    user_note: str | None = None,
    original_url: str | None = None,
    resolved_url: str | None = None,
    user_id: str | None = None,
) -> TextCaptureResponse:
    logger.info("\U0001f4c4 capture.pdf.start filename=%s bytes=%s", filename, len(file_bytes))
    validate_pdf_bytes(file_bytes)
    text, metadata = extract_pdf_text(file_bytes)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    metadata.update(
        {
            "input_kind": "pdf",
            "filename": filename,
            "file_size": len(file_bytes),
            "sha256": file_hash,
            "content_length": len(text),
            "storage_status": "local_only_for_dev",
        }
    )
    return create_extracted_text_capture(
        db=db,
        source_type="pdf",
        raw_text=text,
        title=metadata.get("title") or filename,
        original_url=original_url,
        resolved_url=resolved_url,
        content_hash=file_hash,
        intent_text=intent_text,
        user_note=user_note,
        metadata_json=metadata,
        source_instruction=(
            "This content came from a document. Prioritize principles, definitions, "
            "frameworks, concrete claims, and useful examples over narrative descriptions."
        ),
        extractor=extractor,
        embedder=embedder,
        relation_detector=relation_detector,
        user_id=user_id,
    )


def validate_public_url(url: str, *, enforce_max_length: bool = True) -> str:
    if enforce_max_length and len(url) > MAX_URL_LENGTH:
        raise IngestionError("URL is too long. Maximum URL length is 2048 characters.")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise IngestionError("Only http and https URLs can be captured.")
    if not parsed.hostname:
        raise IngestionError("The URL must include a valid hostname.")
    hostname = parsed.hostname.lower().strip(".")
    if hostname in {"localhost", "0.0.0.0"} or hostname.endswith(".localhost"):
        raise IngestionError("Localhost URLs cannot be captured for security reasons.")

    _assert_hostname_is_public(hostname)
    return url


def fetch_public_url(url: str) -> FetchedContent:
    if not _robots_allows(url):
        raise IngestionError("This site does not allow automated content extraction.")

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5"}
    head = _safe_request("HEAD", url, headers=headers)
    content_type = head.headers.get("content-type", "").split(";", 1)[0].lower()
    resolved_url = str(head.url)
    validate_public_url(resolved_url)

    if head.status_code >= 400 or not content_type or head.status_code == 405:
        logger.info("\U0001f517 capture.url.head_fallback status=%s", head.status_code)

    response = _safe_request("GET", resolved_url, headers=headers)
    content_type = response.headers.get("content-type", content_type).split(";", 1)[0].lower()
    if len(response.content) > MAX_FETCH_BYTES:
        raise IngestionError("This URL is too large to process safely.")
    return FetchedContent(url=str(response.url), content_type=content_type, body=response.content)


def _safe_request(method: str, url: str, *, headers: dict[str, str]) -> httpx.Response:
    current = validate_public_url(url, enforce_max_length=False)
    with httpx.Client(timeout=15.0, follow_redirects=False, headers=headers) as client:
        for _ in range(6):
            response = client.request(method, current)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            current = validate_public_url(urljoin(current, location), enforce_max_length=False)
        raise IngestionError("This URL redirects too many times.")


def _assert_hostname_is_public(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise IngestionError("Crowscap could not resolve this URL's hostname.") from exc

    for info in infos:
        ip_text = info[4][0]
        ip = ipaddress.ip_address(ip_text)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise IngestionError("This URL resolves to a private or unsafe network address.")


def _robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        response = _safe_request("GET", robots_url, headers={"User-Agent": USER_AGENT})
    except IngestionError:
        return True
    if response.status_code >= 400:
        return True
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def _looks_like_html(content_type: str) -> bool:
    return content_type in {"text/html", "application/xhtml+xml", ""}


def extract_article_text(body: bytes, *, url: str) -> str:
    try:
        import trafilatura
    except ImportError as exc:
        raise IngestionError("Article extraction is not installed. Install trafilatura.") from exc

    html_text = body.decode("utf-8", errors="replace")
    extracted = trafilatura.extract(
        html_text,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    article = _normalize_text(extracted or "")
    if len(article) < MIN_EXTRACTED_CHARS:
        fallback = _HTMLTextExtractor()
        fallback.feed(html_text)
        article = fallback.text()
    if len(article) < MIN_EXTRACTED_CHARS:
        raise IngestionError("Crowscap could not extract readable article text from this page.")
    return article


def extract_youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().strip(".")
    path = parsed.path.rstrip("/")
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/", 1)[0]
        return _normalize_youtube_video_id(video_id)
    if host.endswith("youtube.com"):
        if path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            return _normalize_youtube_video_id(video_id)
        for prefix in ("/shorts/", "/embed/", "/live/"):
            if path.startswith(prefix):
                video_id = path.split(prefix, 1)[1].split("/", 1)[0]
                return _normalize_youtube_video_id(video_id)
    return None


def _normalize_youtube_video_id(video_id: str | None) -> str | None:
    if not video_id:
        return None
    cleaned = video_id.strip().split("?", 1)[0].split("&", 1)[0]
    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", cleaned) is None:
        return None
    return cleaned


def unsupported_url_reason(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().strip(".")
    if host == "chat.whatsapp.com":
        return (
            "WhatsApp group invite links do not contain readable source text for Crowscap to extract. "
            "Nothing has been saved from this link."
        )
    return None


def _choose_caption_track(info: dict[str, Any]) -> dict[str, str] | None:
    subtitles = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}
    choices = [
        ("manual", "en", subtitles.get("en")),
        ("automatic", "en", automatic.get("en")),
    ]
    for language, tracks in subtitles.items():
        choices.append(("manual", language, tracks))
    for language, tracks in automatic.items():
        choices.append(("automatic", language, tracks))

    for kind, language, tracks in choices:
        if not tracks:
            continue
        selected = _pick_caption_format(tracks)
        if selected:
            return {"kind": kind, "language": language, "url": selected["url"]}
    return None


def _pick_caption_format(tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
    preferred = ("vtt", "srv3", "ttml", "json3")
    for ext in preferred:
        for track in tracks:
            if track.get("ext") == ext and track.get("url"):
                return track
    return next((track for track in tracks if track.get("url")), None)


def _download_caption_text(url: str) -> str:
    response = _safe_request("GET", url, headers={"User-Agent": USER_AGENT})
    return response.text


def clean_transcript(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            return _normalize_text(_json3_caption_to_text(stripped))
        except json.JSONDecodeError:
            pass

    lines: list[str] = []
    previous = ""
    for line in raw.splitlines():
        line = html.unescape(line.strip())
        if not line or line.upper().startswith("WEBVTT") or line.startswith("Kind:"):
            continue
        if "-->" in line or re.match(r"^\d+$", line):
            continue
        line = re.sub(r"<[^>]+>", " ", line)
        line = re.sub(r"\[(music|applause|inaudible|laughter).*?\]", " ", line, flags=re.I)
        line = _normalize_text(line)
        if not line or line == previous:
            continue
        lines.append(line)
        previous = line
    return _normalize_text(" ".join(lines))


def _json3_caption_to_text(raw: str) -> str:
    data = json.loads(raw)
    parts: list[str] = []
    for event in data.get("events", []):
        for segment in event.get("segs", []) or []:
            text = segment.get("utf8")
            if text:
                parts.append(text)
    return " ".join(parts)


def validate_pdf_bytes(file_bytes: bytes) -> None:
    if len(file_bytes) > MAX_PDF_BYTES:
        raise IngestionError("This PDF is larger than 10MB. Please upload a smaller file.")
    if len(file_bytes) < MIN_PDF_BYTES:
        raise IngestionError("This PDF is too small or empty to process.")
    if not file_bytes.startswith(b"%PDF-"):
        raise IngestionError("This file does not appear to be a valid PDF.")


def extract_pdf_text(file_bytes: bytes) -> tuple[str, dict[str, Any]]:
    try:
        import fitz
    except ImportError as exc:
        raise IngestionError("PDF extraction is not installed. Install PyMuPDF.") from exc

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise IngestionError("Crowscap could not open this PDF. It may be corrupt.") from exc

    page_texts: list[str] = []
    image_like_pages = 0
    for page in document:
        text = page.get_text("text")
        normalized = _normalize_text(text)
        page_texts.append(normalized)
        if len(normalized) < 50:
            image_like_pages += 1

    if not page_texts:
        raise IngestionError("This PDF has no readable pages.")
    if image_like_pages / len(page_texts) > 0.30:
        raise IngestionError(
            "This PDF appears to be a scanned document. Crowscap currently supports text-based PDFs only."
        )

    cleaned = _remove_repeated_page_artifacts(page_texts)
    full_text = _normalize_text("\n\n".join(cleaned))
    if len(full_text) < MIN_EXTRACTED_CHARS:
        raise IngestionError("Crowscap could not extract enough readable text from this PDF.")

    metadata = {
        "title": document.metadata.get("title") or None,
        "author": document.metadata.get("author") or None,
        "creation_date": document.metadata.get("creationDate") or None,
        "page_count": len(page_texts),
        "image_like_pages": image_like_pages,
    }
    document.close()
    return full_text, metadata


def _remove_repeated_page_artifacts(page_texts: list[str]) -> list[str]:
    if len(page_texts) < 3:
        return page_texts

    line_counts: dict[str, int] = {}
    page_lines = []
    for text in page_texts:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        page_lines.append(lines)
        candidates = lines[:2] + lines[-2:]
        for line in candidates:
            if len(line) <= 120:
                line_counts[line] = line_counts.get(line, 0) + 1

    repeated = {
        line
        for line, count in line_counts.items()
        if count >= max(2, int(len(page_texts) * 0.5))
    }
    cleaned_pages = []
    for lines in page_lines:
        cleaned_pages.append("\n".join(line for line in lines if line not in repeated))
    return cleaned_pages


def _normalize_text(value: str) -> str:
    value = value.replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()
