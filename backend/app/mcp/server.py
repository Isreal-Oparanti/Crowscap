from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.mcp.tools import (
    audit_belief_tool,
    get_due_recalls_tool,
    get_user_preferences_tool,
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


def main() -> None:
    mcp.run(transport=settings.crowscap_mcp_transport)

if __name__ == "__main__":
    main()
