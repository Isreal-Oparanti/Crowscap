# MCP Contract

Crowscap exposes a local Model Context Protocol server so an agent can use the
memory system as tools instead of treating it as another web page.

The first MCP version is intentionally read-only. It wraps stable backend
services that already work:

- semantic memory search
- belief audit
- due recall/reminder lookup
- learned user preference lookup

Write tools such as capture, archive, answer recall, and action updates should
come later, after auth and deployment hardening. The first public MCP surface
should not let an external agent mutate a user's memory by accident.

## Local Server

Run from the backend folder:

```powershell
.\.venv\Scripts\python -m app.mcp.server
```

Default local SSE endpoint:

```text
http://127.0.0.1:8010/mcp/sse
```

Default local message endpoint:

```text
http://127.0.0.1:8010/mcp/messages/
```

For ECS later:

```env
CROWSCAP_MCP_HOST=0.0.0.0
CROWSCAP_MCP_PORT=8010
CROWSCAP_MCP_TRANSPORT=sse
CROWSCAP_MCP_SSE_PATH=/mcp/sse
CROWSCAP_MCP_MESSAGE_PATH=/mcp/messages/
```

Then Nginx can proxy the public route to the local MCP process.

## Environment

```env
CROWSCAP_MCP_ENABLED=false
CROWSCAP_MCP_HOST=127.0.0.1
CROWSCAP_MCP_PORT=8010
CROWSCAP_MCP_TRANSPORT=sse
CROWSCAP_MCP_SSE_PATH=/mcp/sse
CROWSCAP_MCP_MESSAGE_PATH=/mcp/messages/
CROWSCAP_MCP_STREAMABLE_HTTP_PATH=/mcp
```

`CROWSCAP_MCP_ENABLED` is a marker for deployment configuration. The MCP server
is currently started as a separate process with `python -m app.mcp.server`.

## Tool: search_memory

Searches saved memories by meaning, not exact words.

Input:

```json
{
  "query": "how do I reach customers?",
  "limit": 5,
  "min_score": 0.25,
  "include_archived": false,
  "user_id": null
}
```

Output:

```json
{
  "query": "how do I reach customers?",
  "min_score": 0.25,
  "candidate_count": 92,
  "embedded_candidate_count": 89,
  "returned_count": 3,
  "top_score": 0.52,
  "results": [
    {
      "memory_id": "uuid",
      "source_id": "uuid",
      "source_type": "text",
      "source_title": "Distribution note",
      "memory_type": "action",
      "epistemic_label": "advice",
      "content": "Test distribution channels early to learn which path reaches customers.",
      "summary": "Test channels early",
      "confidence": "medium",
      "source_strength": "moderate",
      "similarity_score": 0.52
    }
  ]
}
```

## Tool: audit_belief

Synthesizes what the user's saved memories appear to say about a topic. It must
not claim to know the final truth. It reports saved ideas, weak evidence, source
leads, and better questions.

Input:

```json
{
  "topic": "startup distribution",
  "include_public_evidence": true,
  "memory_limit": 8,
  "public_query_count": 3,
  "public_results_per_query": 3,
  "user_id": null
}
```

Output:

```json
{
  "topic": "startup distribution",
  "answer": "Based on saved memories, your view appears to be...",
  "current_understanding": "Distribution is treated as an early learning loop.",
  "strongest_saved_ideas": ["Test distribution channels before launch."],
  "public_evidence_summary": "Public source leads broadly support...",
  "unsupported_or_weak_points": ["The timing depends on product context."],
  "ideas_to_compare": ["Product love may reduce channel friction."],
  "confidence": "medium",
  "confidence_reason": "The saved memories are consistent but not conclusive.",
  "next_questions": ["What signal proves the channel reaches the right users?"],
  "memory_count": 8,
  "public_evidence_count": 3,
  "public_search_status": "searched",
  "public_search_message": null,
  "memories": [],
  "public_evidence": []
}
```

## Tool: get_due_recalls

Returns the next due memory recalls and one-time reminders. This is read-only;
acknowledging or answering a recall remains an HTTP API operation for now.

Input:

```json
{
  "limit": 5,
  "user_id": null
}
```

Output:

```json
{
  "due_count": 2,
  "now": "2026-07-16T12:00:00+00:00",
  "memories": [
    {
      "memory_id": "uuid",
      "source_id": "uuid",
      "source_title": "Distribution note",
      "memory_type": "action",
      "epistemic_label": "advice",
      "content": "Test distribution channels early.",
      "summary": "Test channels early",
      "confidence": "medium",
      "source_strength": "moderate",
      "next_review_at": "2026-07-16T10:00:00+00:00",
      "last_reviewed_at": null,
      "review_count": 0,
      "recall_score": 0.58,
      "overdue_seconds": 7200,
      "recall_prompt": "What is one real situation where this action would matter?",
      "epistemic_caution": "This was saved as advice, not as a verified fact.",
      "relationships": []
    }
  ],
  "reminders": [
    {
      "reminder_id": "uuid",
      "content": "Apply for the founder program",
      "due_at": "2026-07-16T11:55:00+00:00",
      "overdue_seconds": 300,
      "save_as_memory": false,
      "memory_id": null,
      "status": "scheduled"
    }
  ]
}
```

## Tool: get_user_preferences

Returns the durable learning preference profile. This is separate from knowledge
memory: preferences describe how the user wants Crowscap to behave.

Input:

```json
{
  "user_id": null
}
```

Output:

```json
{
  "id": "uuid",
  "user_id": null,
  "preferred_review_time": "evening",
  "recall_frequency": "daily",
  "answer_style": "concise",
  "evidence_strictness": "strict",
  "challenge_style": "direct",
  "memory_density": "compact",
  "notification_preference": "in_app_only",
  "topics_of_interest": ["startups", "product"],
  "source_preferences": {
    "avoid_weak": ["youtube"]
  },
  "updated_from_message_id": "uuid",
  "updated_at": "2026-07-16T12:00:00+00:00"
}
```

## Local Verification

Run the MCP tool contract tests:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests\test_mcp_tools.py
```

Run an import check:

```powershell
.\.venv\Scripts\python -c "from app.mcp.server import mcp; from app.core.config import get_settings; s=get_settings(); print('mcp_loaded', s.crowscap_mcp_host, s.crowscap_mcp_port, s.crowscap_mcp_sse_path)"
```

Expected output shape:

```text
mcp_loaded 127.0.0.1 8010 /mcp/sse
```

## Design Rules

- MCP tools should call service functions, not duplicate business logic.
- Read-only tools ship first; write tools require auth and stronger review.
- Tool outputs should be compact enough for agent context windows.
- Belief audit language must remain epistemically humble: saved memories are not
  automatic truth and not automatic user belief.
- Public deployment should protect the MCP URL before adding mutating tools.
