from pydantic import BaseModel


class SourceContentResponse(BaseModel):
    source_id: str
    source_type: str
    title: str | None
    original_url: str | None
    # The "Original" tab's content. Prefers the organized markdown write-up
    # (Source.summary_markdown) produced by extraction; falls back to the
    # raw captured text (Source.raw_text) when no overview exists yet --
    # e.g. the brief window before a reference link's background
    # enrichment job completes. Markdown-formatted when it's the overview;
    # plain text in the fallback case.
    original_content: str | None
    # True, byte-for-byte captured text, always -- independent of whether
    # `original_content` above is currently the overview or the raw-text
    # fallback. Additive: existing API consumers that only read
    # `original_content` are unaffected.
    raw_text: str | None
