from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.mcp.tools import (
    archive_memory_tool,
    audit_belief_tool,
    capture_text_tool,
    get_due_recalls_tool,
    get_user_preferences_tool,
    quick_recall_tool,
    search_memory_tool,
)

settings = get_settings()

mcp = FastMCP(
    "Crowscap Memory",
    instructions=(
        "Crowscap is a persistent memory system for learned ideas. Use these tools "
        "to search saved memories, audit a user's current understanding, retrieve "
        "due recalls, and read explicit learning preferences. Do not treat Crowscap "
        "as an absolute truth oracle; it surfaces saved evidence, source strength, "
        "uncertainty, and useful questions."
    ),
    host=settings.crowscap_mcp_host,
    port=settings.crowscap_mcp_port,
    sse_path=settings.crowscap_mcp_sse_path,
    message_path=settings.crowscap_mcp_message_path,
    streamable_http_path=settings.crowscap_mcp_streamable_http_path,
)


@mcp.tool()
def search_memory(
    query: str,
    limit: int = 5,
    min_score: float = 0.25,
    include_archived: bool = False,
    user_id: str | None = None,
) -> dict:
    """Search Crowscap memories by semantic meaning, not exact keyword matching."""
    return search_memory_tool(
        query=query,
        limit=limit,
        min_score=min_score,
        include_archived=include_archived,
        user_id=user_id,
    )


@mcp.tool()
def audit_belief(
    topic: str,
    include_public_evidence: bool = True,
    memory_limit: int = 8,
    public_query_count: int = 3,
    public_results_per_query: int = 3,
    user_id: str | None = None,
) -> dict:
    """Audit what the user appears to believe about a topic from saved memories."""
    return audit_belief_tool(
        topic=topic,
        include_public_evidence=include_public_evidence,
        memory_limit=memory_limit,
        public_query_count=public_query_count,
        public_results_per_query=public_results_per_query,
        user_id=user_id,
    )


@mcp.tool()
def get_due_recalls(limit: int = 5, user_id: str | None = None) -> dict:
    """Return memories and reminders that are currently due for recall."""
    return get_due_recalls_tool(limit=limit, user_id=user_id)


@mcp.tool()
def get_user_preferences(user_id: str | None = None) -> dict:
    """Return the learned preference profile that guides Crowscap's behavior."""
    return get_user_preferences_tool(user_id=user_id)


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------


@mcp.tool()
def capture_text(
    content: str,
    user_note: str | None = None,
    intent_text: str | None = None,
    source_title: str | None = None,
    user_id: str | None = None,
) -> dict:
    """[WRITE] Save text to Crowscap memory. Runs the full extraction, embedding, and relationship pipeline. Returns the created memory atoms. content must be at least 20 characters."""
    return capture_text_tool(
        content=content,
        user_note=user_note,
        intent_text=intent_text,
        source_title=source_title,
        user_id=user_id,
    )


@mcp.tool()
def submit_quick_recall(
    memory_id: str,
    action: str,
    user_id: str | None = None,
) -> dict:
    """[WRITE] Submit a quick recall signal for a due memory. action must be one of: still_relevant, applied, not_now. Updates the memory's recall score and schedules the next review. No Qwen call is made."""
    return quick_recall_tool(
        memory_id=memory_id,
        action=action,
        user_id=user_id,
    )


@mcp.tool()
def archive_memory(
    memory_id: str,
    reason: str = "user_dismissed",
    note: str | None = None,
    user_id: str | None = None,
) -> dict:
    """[WRITE] Archive a memory so it stops appearing in recalls and semantic search results. reason must be one of: user_dismissed, not_useful, duplicate, stale, weak_evidence, superseded, other. Creates an audit event."""
    return archive_memory_tool(
        memory_id=memory_id,
        reason=reason,
        note=note,
        user_id=user_id,
    )


def main() -> None:
    mcp.run(transport=settings.crowscap_mcp_transport)

if __name__ == "__main__":
    main()
