# MCP Contract

Crowscap exposes a Model Context Protocol server so an agent can use the
memory system as tools instead of treating it as another web page.

The MCP surface has two tiers:

**Read tools** (safe to call at any time):

- `search_memory` — semantic memory search
- `audit_belief` — belief synthesis over saved memories
- `get_due_recalls` — due recall and reminder lookup
- `get_user_preferences` — learned user preference profile

**Write tools** (mutate user data, scoped by `user_id`):

- `capture_text` — save text through the full extraction and embedding pipeline
- `submit_quick_recall` — acknowledge a due memory without a Qwen evaluation
- `archive_memory` — archive a memory with an audit event

## Current Status

Implemented:

- SSE server process.
- Nginx proxy path for `/mcp/`.
- Four read tools backed by existing Crowscap services.
- Three write tools: `capture_text`, `submit_quick_recall`, `archive_memory`.
- Full tool contract tests (7 tests, all passing).
- Demo agent script at `backend/scripts/demo_agent.py`.

Not complete yet:

- Per-tool authorization policy beyond `user_id` scoping.
- Idempotency keys for repeat-safe capture calls.
- Human-readable confirmation flows for high-impact mutations.
- Rate limiting specific to the MCP surface.
- `create_reminder`, `update_user_preference`, `capture_url_or_reference` tools.

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

---

## Tool: capture_text  *(write)*

Saves text through the full Crowscap extraction and embedding pipeline.
Returns the memory atoms that were created or reused from a duplicate source.

Input:

```json
{
  "content": "Founders who nail distribution before product-market fit often discover that the right channel shapes what the product needs to become.",
  "user_note": "Saved during go-to-market planning.",
  "intent_text": "Remember for strategy work.",
  "source_title": "GTM planning session",
  "user_id": null
}
```

- `content` must be at least 20 characters and at most 10,000 characters.
- `user_note` and `intent_text` are optional context hints for the extractor.
- `source_title` is optional; the extractor infers one if omitted.

Output:

```json
{
  "capture_id": "uuid",
  "source_id": "uuid",
  "source_type": "text",
  "source_title": "GTM planning session",
  "status": "ready",
  "inferred_intents": ["remember", "apply"],
  "memory_count": 2,
  "memories": [
    {
      "id": "uuid",
      "memory_type": "principle",
      "epistemic_label": "advice",
      "content": "The right distribution channel shapes what the product needs to become.",
      "summary": "Channel shapes product.",
      "confidence": "medium",
      "source_strength": "moderate"
    }
  ]
}
```

---

## Tool: submit_quick_recall  *(write)*

Submits a lightweight recall signal for a due memory. No Qwen call is made.
Updates the memory's recall score and schedules the next review date.

Input:

```json
{
  "memory_id": "uuid",
  "action": "still_relevant",
  "user_id": null
}
```

- `action` must be one of: `still_relevant`, `applied`, `not_now`.
- `still_relevant` — memory is still useful; light recall boost.
- `applied` — user acted on it; stronger recall boost.
- `not_now` — defer for 24 hours without changing the recall score.

Output:

```json
{
  "memory_id": "uuid",
  "action": "still_relevant",
  "feedback": "Good. This idea is worth keeping active.",
  "next_due_at": "2026-07-19T12:00:00+00:00",
  "review_count": 3,
  "recall_score": 0.72
}
```

---

## Tool: archive_memory  *(write)*

Archives a memory so it stops appearing in recalls and semantic search results.
Creates a `MemoryArchiveEvent` audit entry.

Input:

```json
{
  "memory_id": "uuid",
  "reason": "superseded",
  "note": "Replaced by a more precise claim saved later.",
  "user_id": null
}
```

- `reason` must be one of: `user_dismissed`, `not_useful`, `duplicate`, `stale`,
  `weak_evidence`, `superseded`, `other`.
- `note` is optional free text recorded in the audit event.

Output:

```json
{
  "memory_id": "uuid",
  "previous_status": "active",
  "new_status": "archived",
  "reason": "superseded",
  "note": "Replaced by a more precise claim saved later.",
  "archived_at": "2026-07-16T14:30:00+00:00"
}
```

## Demo Agent

A standalone demo script chains all seven tools (four reads and three writes)
over a live SSE connection to show the full agent loop:

```powershell
# Start the MCP server
cd backend
.\.venv\Scripts\python -m app.mcp.server

# In a second terminal, run the demo
cd backend
.\.venv\Scripts\python scripts/demo_agent.py
```

To target the live deployed server:

```powershell
.\.venv\Scripts\python scripts/demo_agent.py --url https://api.crowscap.xyz/mcp/sse
```

The demo loop is:

```text
capture_text → search_memory → get_due_recalls → submit_quick_recall
    → audit_belief → get_user_preferences → archive_memory
```

---

## Remaining Planned Tools

These are not yet implemented. They follow the same pattern as the current
write tools: call an existing service function, return a compact dict.

### `capture_url_or_reference`

Capture a readable URL, or save a non-readable/social URL as a reference.

Required safety:

- URL validation and SSRF protections
- explicit `save_mode`: `extract` or `reference`
- clear response when the URL cannot be extracted

### `create_reminder`

Create a one-time reminder, optionally linked to a memory or reference.

Required safety:

- parsed due time
- original user instruction
- `save_as_memory` flag
- no silent long-term memory creation when the user asked only for a reminder

### `update_user_preference`

Update an explicit user preference.

Required safety:

- preference key
- new value
- confidence and source message id
- visible reason so the user can understand why Crowscap adapted

---

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

---

## Design Rules

- MCP tools should call service functions, not duplicate business logic.
- Read tools are always safe; write tools require `user_id` scoping.
- Tool outputs should be compact enough for agent context windows.
- Mutating tool calls create audit events where the service supports it.
- Tools should fail with JSON-shaped, user-safe errors rather than raw tracebacks.
- Belief audit language must remain epistemically humble: saved memories are not
  automatic truth and not automatic user belief.
- Public deployment should protect the MCP URL before adding mutating tools.
