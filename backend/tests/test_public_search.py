from app.schemas.belief import PublicEvidenceResult
from app.services.public_search_service import (
    ChainedPublicSearchProvider,
    PublicSearchError,
    _parse_duckduckgo_results,
)


class FailingProvider:
    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        raise PublicSearchError("Jina public search could not be reached right now.")


class WorkingProvider:
    def search(self, *, query: str, limit: int) -> list[PublicEvidenceResult]:
        return [
            PublicEvidenceResult(
                title="Fallback result",
                url="https://example.com/fallback",
                snippet="Fallback source lead.",
                source="example.com",
                query=query,
                rank=1,
            )
        ][:limit]


def test_chained_public_search_falls_back_after_provider_failure() -> None:
    provider = ChainedPublicSearchProvider([FailingProvider(), WorkingProvider()])

    results = provider.search(query="startup distribution evidence", limit=3)

    assert len(results) == 1
    assert results[0].title == "Fallback result"


def test_duckduckgo_html_parser_extracts_source_leads() -> None:
    html = """
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpost">
        Startup distribution evidence
      </a>
      <a class="result__snippet">A useful source lead about early distribution.</a>
    </div>
    """

    results = _parse_duckduckgo_results(
        html=html,
        query="startup distribution evidence",
        limit=3,
    )

    assert len(results) == 1
    assert results[0].url == "https://example.com/post"
    assert results[0].source == "example.com"
    assert results[0].snippet == "A useful source lead about early distribution."
