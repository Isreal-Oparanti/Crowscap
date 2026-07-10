from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.belief import PublicEvidenceResult

logger = get_logger("services.public_search")


class PublicSearchError(RuntimeError):
    """Raised when a public evidence provider cannot be queried."""


class PublicSearchProvider(Protocol):
    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        pass


class DisabledPublicSearchProvider:
    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        logger.info("🌐 public_search.disabled query_chars=%s limit=%s", len(query), limit)
        return []


class ChainedPublicSearchProvider:
    def __init__(self, providers: list[PublicSearchProvider]) -> None:
        self.providers = providers

    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        failures: list[str] = []
        for provider in self.providers:
            try:
                results = provider.search(query=query, limit=limit)
            except PublicSearchError as exc:
                failures.append(str(exc))
                continue
            if results:
                return results

        if failures:
            raise PublicSearchError("; ".join(dict.fromkeys(failures)))
        return []


class JinaPublicSearchProvider:
    """Small no-key public search adapter.

    Jina's search endpoint returns text/markdown. We parse defensively and treat
    results as source leads, not settled evidence.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        logger.info("🌐 public_search.start provider=jina query=%r limit=%s", query, limit)
        text = self._request(query=query)
        results = _parse_jina_results(text=text, query=query, limit=limit)
        logger.info("✅ public_search.complete provider=jina query=%r results=%s", query, len(results))
        return results

    def _request(self, *, query: str) -> str:
        base_url = self.settings.public_search_base_url.rstrip("/") + "/"
        headers = {
            "Accept": "text/plain",
            "User-Agent": "Crowscap/0.1 belief-audit",
        }
        timeout = self.settings.public_search_timeout_seconds

        try:
            response = httpx.get(
                base_url,
                params={"q": query},
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )
            if response.status_code == 404 or len(response.text.strip()) < 50:
                path_response = httpx.get(
                    f"{base_url}{quote(query)}",
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=True,
                )
                path_response.raise_for_status()
                return path_response.text

            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            logger.warning("⚠️ public_search.failed provider=jina query=%r reason=%s", query, exc)
            raise PublicSearchError("Jina public search could not be reached right now.") from exc


class DuckDuckGoPublicSearchProvider:
    """No-key HTML search fallback used only for public source leads."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        logger.info("🌐 public_search.start provider=duckduckgo query=%r limit=%s", query, limit)
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 Crowscap/0.1 belief-audit",
        }
        try:
            response = httpx.get(
                self.settings.public_search_duckduckgo_url,
                params={"q": query},
                headers=headers,
                timeout=self.settings.public_search_timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("⚠️ public_search.failed provider=duckduckgo query=%r reason=%s", query, exc)
            raise PublicSearchError("DuckDuckGo public search could not be reached right now.") from exc

        results = _parse_duckduckgo_results(html=response.text, query=query, limit=limit)
        logger.info(
            "✅ public_search.complete provider=duckduckgo query=%r results=%s",
            query,
            len(results),
        )
        return results


def get_public_search_provider() -> PublicSearchProvider:
    settings = get_settings()
    if settings.public_search_provider == "disabled":
        return DisabledPublicSearchProvider()
    if settings.public_search_provider == "duckduckgo":
        return DuckDuckGoPublicSearchProvider()
    return ChainedPublicSearchProvider([JinaPublicSearchProvider(), DuckDuckGoPublicSearchProvider()])


def _parse_jina_results(*, text: str, query: str, limit: int) -> list[PublicEvidenceResult]:
    chunks = _split_result_chunks(text)
    results: list[PublicEvidenceResult] = []
    seen_urls: set[str] = set()

    for chunk in chunks:
        title = _first_match(chunk, r"(?:^|\n)\s*(?:\[\d+\]\s*)?Title:\s*(.+)")
        url = _first_match(chunk, r"(?:^|\n)\s*(?:URL Source|URL|Link):\s*(https?://\S+)")
        snippet = _first_match(chunk, r"(?:^|\n)\s*(?:Description|Snippet):\s*(.+)")

        if not title or not url:
            markdown = re.search(r"\[([^\]]{3,200})\]\((https?://[^)]+)\)", chunk)
            if markdown:
                title = title or markdown.group(1)
                url = url or markdown.group(2)

        if not title or not url:
            continue

        clean_url = url.rstrip(").,;")
        if clean_url in seen_urls:
            continue

        seen_urls.add(clean_url)
        if not snippet:
            snippet = _fallback_snippet(chunk)

        results.append(
            PublicEvidenceResult(
                title=_clean_text(title)[:300],
                url=clean_url,
                snippet=_clean_text(snippet)[:800] if snippet else None,
                source=_source_from_url(clean_url),
                query=query,
                rank=len(results) + 1,
            )
        )
        if len(results) >= limit:
            break

    return results


def _parse_duckduckgo_results(
    *,
    html: str,
    query: str,
    limit: int,
) -> list[PublicEvidenceResult]:
    parser = _DuckDuckGoResultParser()
    parser.feed(html)
    results: list[PublicEvidenceResult] = []
    seen_urls: set[str] = set()

    for item in parser.results:
        url = _normalize_duckduckgo_url(item.url)
        title = _clean_text(item.title)
        if not url or not title or url in seen_urls:
            continue

        seen_urls.add(url)
        results.append(
            PublicEvidenceResult(
                title=title[:300],
                url=url,
                snippet=_clean_text(item.snippet)[:800] if item.snippet else None,
                source=_source_from_url(url),
                query=query,
                rank=len(results) + 1,
            )
        )
        if len(results) >= limit:
            break

    return results


class _DuckDuckGoResult:
    def __init__(self, title: str = "", url: str = "", snippet: str = "") -> None:
        self.title = title
        self.url = url
        self.snippet = snippet


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[_DuckDuckGoResult] = []
        self._current: _DuckDuckGoResult | None = None
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        class_name = attr_map.get("class", "")

        if tag == "a" and "result__a" in class_name:
            self._current = _DuckDuckGoResult(url=attr_map.get("href", ""))
            self._capture_title = True
            return

        if self._current and "result__snippet" in class_name:
            self._capture_snippet = True

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        if self._capture_title:
            self._current.title += data
        elif self._capture_snippet:
            self._current.snippet += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title:
            self._capture_title = False
            if self._current is not None:
                self.results.append(self._current)
            return

        if self._capture_snippet and tag in {"a", "div"}:
            self._capture_snippet = False


def _normalize_duckduckgo_url(url: str) -> str | None:
    clean = unescape(url).strip()
    if clean.startswith("//"):
        clean = "https:" + clean

    parsed = urlparse(clean)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        clean = unquote(target) if target else clean

    if not clean.startswith(("http://", "https://")):
        return None
    return clean.rstrip(").,;")


def _split_result_chunks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    chunks = re.split(r"(?=\n\s*(?:\[\d+\]\s*)?Title:\s*)", normalized)
    if len(chunks) > 1:
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    return [line.strip() for line in normalized.split("\n\n") if line.strip()]


def _first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _fallback_snippet(chunk: str) -> str | None:
    lines = [
        line.strip()
        for line in chunk.splitlines()
        if line.strip()
        and not re.match(r"^(?:\[\d+\]\s*)?(Title|URL Source|URL|Link):", line, re.IGNORECASE)
    ]
    text = " ".join(lines)
    return text[:800] if text else None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _source_from_url(url: str) -> str | None:
    match = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else None
