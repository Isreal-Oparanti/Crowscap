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

## Chat

### POST /chat

The main conversational gateway. It prevents the frontend from treating every
non-question as a memory.

Request:

```json
{
  "message": "okay this makes sense thanks",
  "history": []
}
```

Response:

```json
{
  "action": "acknowledge",
  "message": "You are welcome. I am glad it makes sense.",
  "saved": false,
  "capture": null,
  "evidence": [],
  "knowledge_gaps": [],
  "tensions": [],
  "next_step": null
}
```

`action` is one of `acknowledge`, `capture`, or `answer`.

## Captures

### POST /captures/text

Phase 0 implemented endpoint. Captures plain text, extracts memory atoms with Qwen, embeds each memory, deduplicates by content hash, and runs relationship detection against older memories.

Request:

```json
{
  "content": "A founder should not wait until launch to think about distribution...",
  "intent_text": "remember and apply this to my startup",
  "user_note": "I keep hearing distribution matters but want to use it.",
  "source_title": "Distribution learning note"
}
```

Response:

```json
{
  "capture_id": "uuid",
  "source_id": "uuid",
  "source_title": "Distribution learning note",
  "original_content": "A founder should not wait until launch to think about distribution...",
  "status": "ready",
  "inferred_intents": ["remember", "apply"],
  "memories": [
    {
      "id": "uuid",
      "memory_type": "principle",
      "epistemic_label": "advice",
      "content": "A founder should not wait until launch to think about distribution.",
      "summary": "Do not delay distribution planning until launch",
      "confidence": "medium",
      "confidence_reason": "The source presents this as advice rather than measured evidence.",
      "source_strength": "moderate",
      "embedding_dimensions": 1024,
      "relationships": [
        {
          "related_memory_id": "uuid",
          "relationship_type": "tension",
          "strength": "moderate",
          "explanation": "The newer idea emphasizes product love while the older memory emphasizes early distribution testing."
        }
      ]
    }
  ]
}
```

`original_content` is the exact text the user submitted. Memory atoms are derived intelligence; the original remains available as the source-of-record.

### GET /sources/{source_id}

Returns source metadata and the exact captured text for reference views and recall.

```json
{
  "source_id": "uuid",
  "source_type": "text",
  "title": "Distribution learning note",
  "original_url": null,
  "original_content": "A founder should not wait until launch..."
}
```

Older development captures may return `original_content: null`. Re-submitting the identical text backfills it through the duplicate-capture path without rerunning extraction.

### POST /captures

Future generalized endpoint. Creates a capture and queues processing for URLs, PDFs, videos, and other sources.

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
  "min_score": 0.25,
  "candidate_count": 12,
  "embedded_candidate_count": 10,
  "returned_count": 3,
  "top_score": 0.526463,
  "results": [
    {
      "memory_id": "uuid",
      "source_id": "uuid",
      "source_title": "YC sales video",
      "content": "Early startups should test distribution before over-investing in product polish.",
      "memory_type": "principle",
      "epistemic_label": "advice",
      "confidence": "medium",
      "confidence_reason": "The source presents this as founder advice.",
      "source_strength": "moderate",
      "similarity_score": 0.526463,
      "embedding_dimensions": 1024
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

Phase 0 implemented endpoint. Returns active memories where `next_review_at` is in the past, ordered by most overdue first.

Query params:
- limit: optional, default 50, max 100

Response:

```json
{
  "due_count": 1,
  "now": "2026-06-14T14:00:00Z",
  "memories": [
    {
      "memory_id": "uuid",
      "source_id": "uuid",
      "source_title": "Distribution note",
      "memory_type": "principle",
      "epistemic_label": "advice",
      "content": "Distribution should be tested early.",
      "summary": "Test distribution early",
      "confidence": "medium",
      "confidence_reason": "The source presents this as advice.",
      "source_strength": "moderate",
      "next_review_at": "2026-06-14T08:00:00Z",
      "last_reviewed_at": null,
      "review_count": 0,
      "recall_score": 0.5,
      "overdue_seconds": 21600,
      "relationships": [
        {
          "related_memory_id": "uuid",
          "related_memory_content": "Distribution cannot rescue a product nobody wants.",
          "relationship_type": "tension",
          "strength": "moderate",
          "explanation": "Both ideas matter but pull in different directions.",
          "direction": "incoming"
        }
      ]
    }
  ]
}
```

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
  "review_id": "uuid",
  "memory_id": "uuid",
  "feedback": "Good central idea. You missed the source's point about testing channel fit before scaling.",
  "score": 0.74,
  "rating": "solid",
  "understanding_summary": "Distribution testing reveals whether a product can reliably reach the customers it is designed for.",
  "knowledge_gaps": [
    "The answer did not distinguish channel reach from actual product demand."
  ],
  "context_to_consider": [
    "This is advice from a moderate-strength source, not a universal law."
  ],
  "next_question": "What signal would separate channel failure from product failure?",
  "next_due_at": "2026-06-15T09:00:00Z",
  "review_count": 2,
  "recall_score": 0.72
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
