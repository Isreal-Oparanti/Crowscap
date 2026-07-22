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
  "next_step": null,
  "preference_updates": [],
  "preferences": null
}
```

`action` is one of `acknowledge`, `conversation`, `capture`, `answer`, `audit`, `forget`, `reminder`, `self`, or `recent`.

Input limits and tolerance:

- `message` accepts up to 40,000 characters. Long pastes are the core capture
  use case and must never be rejected for ordinary lengths.
- `history` is advisory context only; the server prefers its own persisted
  conversation history. Client-sent history turns are truncated to 4,000
  characters and capped at the last 12 turns instead of being rejected.
  Hard-rejecting oversized history once caused a poisoned-conversation bug:
  after one long paste, every later request in that chat failed validation.
- `preference_updates` and `preferences` are populated only on `acknowledge`
  turns where the whole message was an explicit preference command. Incidental
  preference learning never surfaces in chat responses.

When the user explicitly states a preference, the same endpoint updates the durable preference profile without saving a memory:

```json
{
  "message": "I prefer short answers. Challenge my assumptions more."
}
```

Response excerpt:

```json
{
  "action": "acknowledge",
  "saved": false,
  "preference_updates": [
    "Answer style: concise",
    "Challenge style: direct"
  ],
  "preferences": {
    "answer_style": "concise",
    "challenge_style": "direct",
    "evidence_strictness": "balanced"
  }
}
```

## Preferences

### GET /preferences/me

Returns the durable preference profile that Crowscap uses to adapt chat, recall, and belief audits.

Response:

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
    "avoid_weak": ["youtube"],
    "rule": "avoid weak sources unless corroborated by stronger evidence"
  },
  "confidence_scores": {
    "answer_style": 0.9,
    "topics_of_interest": 0.55
  },
  "inferred_topics": ["startup", "backend"],
  "deprioritized_topics": [],
  "deprioritized_memory_types": ["quote"],
  "content_affinities": {
    "source_types": {
      "youtube": 4,
      "text": 3
    },
    "memory_types": {
      "principle": 9,
      "action": 5
    },
    "strong_recall_memory_types": ["action"]
  },
  "learning_signals": [
    "Recurring topics inferred from saved memories: startup, backend."
  ],
  "last_autonomous_update_at": "2026-07-17T12:00:00Z",
  "updated_from_message_id": "uuid",
  "updated_at": "2026-07-14T12:00:00Z"
}
```

Explicit user preferences are treated as high-confidence. Behavior-derived fields such as `inferred_topics`, `content_affinities`, and `deprioritized_memory_types` are lower-confidence signals and should be displayed as things Crowscap has noticed, not as unquestionable facts.

### POST /preferences/learn-now

Forces the autonomous preference accumulator to run immediately for the current user. This is useful in development and demos because the normal chat path throttles autonomous updates to roughly once per 24 hours.

Response:

```json
{
  "preferences": {
    "id": "uuid",
    "answer_style": "concise",
    "topics_of_interest": ["startups", "backend"],
    "inferred_topics": ["startup", "backend"],
    "learning_signals": [
      "Recurring topics inferred from saved memories: startup, backend."
    ]
  },
  "updates": [
    "Recurring topics inferred from saved memories: startup, backend."
  ]
}
```

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

### GET /memories/perspective-notes/due

Returns perspective notes that are ready to surface for the signed-in user. Perspective notes are delayed, non-judgmental prompts linked to under-evidenced or one-sided memories.

Query params:
- limit: optional, default 10, max 50
- include_future: optional, default false. Set true during development to inspect queued notes before their surface date.

Response:

```json
{
  "count": 1,
  "notes": [
    {
      "id": "uuid",
      "memory_id": "uuid",
      "memory_content": "Polling is the best way to handle chat notifications in the backend.",
      "source_title": "Backend note",
      "status": "queued",
      "perspective_type": "nuance",
      "title": "Consider where this may not apply",
      "content": "You saved this idea, but Crowscap should not treat it as settled truth yet. When it resurfaces, compare it against a credible counterexample, boundary condition, or stronger source before deciding whether to keep, refine, or replace the belief.",
      "suggested_query": "Polling is the best way to handle chat notifications in the backend counterarguments evidence limitations",
      "confidence": "medium",
      "surface_after_at": "2026-07-20T12:00:00Z",
      "created_at": "2026-07-17T12:00:00Z"
    }
  ]
}
```

### POST /memories/perspective-notes/{note_id}/accept

Marks a perspective note as useful. It does not automatically create a new memory yet.

### POST /memories/perspective-notes/{note_id}/dismiss

Stops surfacing a perspective note.

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

Local MCP/SSE endpoint:

```text
http://127.0.0.1:8010/mcp/sse
```

Implemented read-only tools:

- `search_memory`: semantic search over saved memory atoms.
- `audit_belief`: source-aware belief audit over saved memories and optional public evidence leads.
- `get_due_recalls`: due memories and one-time reminders.
- `get_user_preferences`: learned preference profile.

Write tools are intentionally deferred:

- `capture_memory`
- `answer_recall`
- `archive_memory`
- `complete_reminder`
- `update_action`

Reason: external agent write access needs authentication, ownership checks, and
confirmation behavior. The first MCP surface is read-only so judges can inspect
and call the memory system without risking accidental mutation.

Full contract: `docs/15-mcp-contract.md`.
