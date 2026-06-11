# Backend Architecture

## Stack Decision

Use FastAPI + Pydantic v2 + SQLAlchemy 2.x + Alembic.

Why:
- FastAPI gives clean typed HTTP APIs and OpenAPI docs.
- Pydantic lets us validate Qwen structured outputs and API contracts.
- SQLAlchemy and Alembic give mature relational modeling and migrations.
- Python has strong libraries for extraction, PDFs, background jobs, and AI orchestration.

## Queue Decision

Use Redis + Celery for the first production-minded version.

Why not BullMQ first:
- BullMQ is a Node.js queue.
- Our backend is Python.
- Using BullMQ would require a Node worker or cross-runtime job processor.
- That adds architecture surface area without improving the hackathon core.

Alternatives:
- RQ: simpler Python queue, good for MVP.
- arq: async Redis queue, good with asyncio.
- Dramatiq: strong task queue, simpler than Celery.

Chosen path:
- Celery for retries, delayed jobs, worker separation, and scheduled tasks through Celery Beat.
- If Celery becomes too heavy during implementation, fall back to RQ and document the decision.

## Backend Folder Structure

```text
backend/
  app/
    __init__.py
    main.py
    api/
      v1/
        captures.py
        memories.py
        recalls.py
        audits.py
        search.py
        health.py
    core/
      config.py
      logging.py
      security.py
      errors.py
    db/
      base.py
      session.py
      models/
      repositories/
      migrations/
    schemas/
      capture.py
      memory.py
      recall.py
      audit.py
      job.py
    services/
      capture_service.py
      extraction_service.py
      memory_service.py
      relation_service.py
      recall_service.py
      audit_service.py
      search_service.py
    ai/
      qwen_client.py
      prompts/
      structured_outputs.py
      validators.py
    ingestion/
      url_safety.py
      router.py
      extractors/
        article.py
        youtube.py
        pdf.py
        plaintext.py
      chunking.py
      cleaning.py
    workers/
      celery_app.py
      tasks.py
      schedules.py
    mcp/
      server.py
      tools.py
    evals/
      datasets/
      naive_rag.py
      crowscap_retrieval.py
      metrics.py
  tests/
    unit/
    integration/
    evals/
  pyproject.toml
  alembic.ini
  Dockerfile
```

## Backend Request Pattern

Do not perform slow extraction inside the HTTP request.

Pattern:

1. API validates request.
2. API creates capture and source records.
3. API enqueues `process_capture` job.
4. API returns `202 Accepted` with `job_id`.
5. Frontend polls job status or subscribes to status updates.
6. Worker extracts, chunks, calls Qwen, stores memories, schedules recall.

## Qwen Client

Use the OpenAI-compatible SDK with:

```text
base_url = https://dashscope-intl.aliyuncs.com/compatible-mode/v1
api key env = DASHSCOPE_API_KEY
```

Source: Qwen Cloud first API call documentation.

Recommended model environment variables:

```text
QWEN_REASONING_MODEL=qwen3.7-plus
QWEN_FAST_MODEL=qwen3.6-flash
QWEN_EMBEDDING_MODEL=text-embedding-v4
QWEN_RERANK_MODEL=qwen3-rerank
```

Do not hardcode these in business logic. Model names and pricing can change.

## Structured Output Policy

Qwen Cloud structured output uses `response_format={"type":"json_object"}` and the prompt must include the word JSON. It guarantees valid JSON output, but not schema correctness.

Backend rule:
- Every Qwen JSON response must pass through Pydantic validation.
- Invalid schema should trigger repair once using a fast model, then fail gracefully.
- Store raw model output for debugging when safe.
- Do not combine structured output with Qwen thinking mode in the first build; Qwen docs describe structured output for non-thinking mode and provide a repair workaround for thinking-mode outputs.
- Avoid arbitrary low `max_tokens` values for structured output because truncation can break JSON.

## Background Task Pipeline

`process_capture(capture_id)`:

1. Load capture and source.
2. Run URL/file/text safety checks.
3. Extract text or transcript.
4. Clean boilerplate and normalize whitespace.
5. Chunk long content.
6. Classify capture intent if user intent is missing or ambiguous.
7. Extract atomic memories per chunk.
8. Merge/deduplicate memory atoms.
9. Generate embeddings.
10. Store memory atoms.
11. Retrieve nearby existing memories.
12. Classify relations/tensions.
13. Generate recall prompts and schedule.
14. Update job status and notify frontend.

## Services

CaptureService:
- Creates capture/source records.
- Starts processing jobs.
- Handles user intent.

ExtractionService:
- Routes source to proper extractor.
- Returns clean extracted text and metadata.

MemoryService:
- Persists memory atoms.
- Handles deduplication and embedding records.

RelationService:
- Finds candidate related memories.
- Classifies relationship type.
- Stores memory graph edges.

RecallService:
- Creates and updates recall schedules.
- Scores due memories.
- Grades user recall attempts with Qwen when needed.

AuditService:
- Retrieves topic-related memories.
- Synthesizes stance, repeated ideas, weak assumptions, tensions, and action gaps.

SearchService:
- Performs hybrid search.
- Combines vector similarity, filters, source metadata, and optional reranking.

## Testing Strategy

Unit tests:
- URL safety.
- Chunking.
- Pydantic schema validation.
- Recall scoring.
- Relation classification parser.
- Deduplication.

Integration tests:
- Capture raw text end to end with fake Qwen client.
- PDF extraction.
- Article extraction fallback.
- Database migrations.
- Job processing.

Evaluation tests:
- Naive chunk retrieval vs atomic memory retrieval.
- Context token estimate.
- Precision of retrieved memory atoms.
- Tension detection examples.
