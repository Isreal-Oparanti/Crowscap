# API Contract

Base path:

```text
/api/v1
```

## Health

### GET /health

Returns service status.

Response:

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

## Captures

### POST /captures

Creates a capture and queues processing.

Request:

```json
{
  "input_type": "url",
  "content": "https://example.com/article",
  "user_note": "Remember this for startup distribution",
  "intent_text": "apply this later"
}
```

Response:

```json
{
  "capture_id": "uuid",
  "source_id": "uuid",
  "job_id": "uuid",
  "status": "queued"
}
```

### GET /captures/{capture_id}

Returns capture, source, job status, and extracted memories if ready.

### POST /captures/{capture_id}/retry

Retries a failed extraction job.

### POST /captures/{capture_id}/archive

Archives a capture and optionally its memories.

## Jobs

### GET /jobs/{job_id}

Response:

```json
{
  "job_id": "uuid",
  "status": "running",
  "step": "extracting_memories",
  "progress": 0.65,
  "error_code": null
}
```

## Memories

### GET /memories

Query params:
- status
- type
- tag
- source_id
- limit
- cursor

### GET /memories/{memory_id}

Returns full memory, source metadata, relations, and recall history.

### POST /memories/{memory_id}/feedback

Request:

```json
{
  "rating": "useful",
  "note": "This is important for my current project"
}
```

### POST /memories/{memory_id}/archive

Archives a memory.

## Search

### POST /search

Request:

```json
{
  "query": "what have I saved about distribution?",
  "include_archived": false,
  "limit": 10
}
```

Response:

```json
{
  "query": "what have I saved about distribution?",
  "results": [
    {
      "memory_id": "uuid",
      "content": "Early startups should test distribution before over-investing in product polish.",
      "memory_type": "principle",
      "confidence": "medium",
      "source": {
        "title": "YC sales video",
        "url": "https://youtube.com/..."
      },
      "score": 0.82
    }
  ]
}
```

## Audits

### POST /audits

Request:

```json
{
  "topic": "startup distribution",
  "user_context": "I am validating an AI product idea"
}
```

Response:

```json
{
  "audit_id": "uuid",
  "topic": "startup distribution",
  "apparent_stance": "Based on what you saved, your current stance appears to be that distribution should be tested early, not treated as a post-product activity.",
  "repeated_ideas": [],
  "strongest_sources": [],
  "weakest_assumptions": [],
  "tensions": [],
  "action_gaps": [],
  "suggested_prompt": "You have saved the idea that distribution matters several times. What specific distribution experiment are you running this week?"
}
```

## Recalls

### GET /recalls/due

Returns due recall prompts.

### POST /recalls/{recall_id}/answer

Request:

```json
{
  "answer": "Distribution means the path by which customers discover and adopt the product...",
  "self_rating": 3
}
```

Response:

```json
{
  "feedback": "Good central idea. You missed the source's point about testing channel fit before scaling.",
  "score": 0.74,
  "next_due_at": "2026-06-15T09:00:00Z"
}
```

## MCP Tools

Expose equivalent operations through MCP:

- capture_memory
- search_memory
- get_due_recalls
- answer_recall
- audit_topic
- compare_memories
- archive_memory

Qwen Cloud MCP support uses the Responses API and currently supports SSE MCP servers according to Qwen Cloud documentation. The docs also state MCP is available through the Responses API only. Keep MCP as a separate service layer that calls internal backend services.
