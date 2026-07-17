# System Architecture

## Architecture Goal

Build a production-minded agent system where capture, extraction, memory storage, recall, audit, and evaluation are modular. The system should be easy for judges to understand and easy for us to extend after the hackathon.

## High-Level Components

Frontend:
- Next.js application for capture, inbox, memory cards, recall queue, search, and audits.

Backend API:
- FastAPI service for authenticated HTTP endpoints.
- Owns orchestration, validation, and API contracts.

Worker:
- Background processor for extraction, chunking, Qwen calls, embeddings, relation detection, recall scheduling, and cleanup.

Database:
- PostgreSQL stores users, preference profiles, captures, sources, chunks, memories, relations, recall events, audit records, and jobs.
- Vector extension or vector-capable storage is used for semantic memory retrieval.

Redis:
- Broker/cache for background jobs, status updates, and short-lived extraction cache.

Qwen Cloud:
- Chat/completion for extraction, classification, relation detection, recall prompts, and audit synthesis.
- Embeddings for semantic search.
- Optional reranker for retrieval quality.
- Optional MCP integration through the Responses API.

Object Storage:
- Stores uploaded PDFs, source snapshots, extracted transcripts, screenshots, and raw artifacts.

MCP Server:
- Exposes memory tools to agent clients and Qwen Cloud MCP-compatible flows.

Evaluation Harness:
- Runs repeatable comparisons against naive RAG.

## System Diagram

See [system.mmd](diagrams/system.mmd).

## Main Runtime Flow

```text
User -> Frontend -> FastAPI -> DB
                         |
                         v
                    Job Queue
                         |
                         v
                      Worker
       +-----------------+------------------+
       |                                    |
       v                                    v
  Extract/Chunk                        Qwen Cloud
       |                                    |
       v                                    v
  Store Source/Chunks -> Atomic Memories -> Embeddings -> Relations -> Recall Schedule
```

## Preference Memory Layer

Preference memory is separate from semantic memory. It stores how the user wants Crowscap to behave, not what the user learned.

The layer has two confidence tiers:

- Explicit preferences: direct user statements such as "I prefer short answers", "challenge my assumptions", "remind me in the evenings", or "do not show weak YouTube advice unless there is evidence".
- Autonomous signals: lower-confidence patterns inferred from captures, archives, recall reviews, source mix, and memory types.

Autonomous updates are throttled and database-first. They do not call Qwen on every message. This keeps the adaptation loop cheap, explainable, and safe from overfitting.

The profile currently affects:
- Chat synthesis: answer length, directness, and evidence framing.
- Belief audit: strictness around evidence and how directly Crowscap pushes back.
- Recall prompts: whether review questions are concise, evidence-focused, or more challenging.

This is the core Track 1 adaptation layer: Crowscap persists not only what the user has learned, but how the user wants to learn.

## Perspective Note Layer

Perspective notes sit between passive storage and active correction. When a saved memory looks under-evidenced or one-sided, Crowscap queues a delayed note that asks the user to compare the memory with a counterexample, boundary condition, or stronger source.

The system does not immediately declare the saved idea wrong. It surfaces a future prompt and lets the user accept or dismiss it. This preserves trust while still helping the user repair knowledge gaps over time.

## Recommended Service Boundaries

API service:
- Thin request validation.
- Auth/session handling.
- Job creation.
- Query endpoints.
- Response shaping.

Worker service:
- URL extraction.
- PDF processing.
- Transcript processing.
- Qwen structured extraction.
- Embedding generation.
- Memory relation detection.
- Recall scheduling.
- Archive/forgetting jobs.

MCP service:
- Tool definitions.
- Calls internal backend services.
- Should not duplicate memory logic.

Frontend:
- Does not call Qwen directly.
- Does not own business logic.
- Renders status, results, and user interactions.

## Local Development Shape

```text
docker compose
  postgres
  redis
  backend-api
  backend-worker
  frontend
```

Initial implementation can run API and worker locally without Docker, but the repository should include Docker instructions for judges.

## Deployment Shape

Required by hackathon:
- Backend must run on Alibaba Cloud.
- Repository must include a code file demonstrating use of Alibaba Cloud services/APIs.

Recommended:
- ECS instance or container service for FastAPI and worker.
- Managed Redis or Redis container for hackathon simplicity.
- PostgreSQL with vector support if available in the chosen Alibaba Cloud database option.
- If managed vector support is not available in the chosen setup, use Postgres + pgvector in a Docker container on ECS for the hackathon and document that choice clearly.
- OSS for uploaded artifacts and source snapshots.

## Architectural Risks

1. Extraction is messy:
   Many URLs fail due to JavaScript rendering, bot blocks, paywalls, or missing transcripts.

2. Qwen JSON can be valid but not schema-conformant:
   Structured output guarantees valid JSON mode, not business-schema correctness. Pydantic validation is still required.

3. Contradiction is not binary:
   Store relation types such as supports, challenges, depends_on_context, repeats, updates, and weakens.

4. Graph UI can distract:
   The audit page is the core product surface. Graph views should be secondary.

5. Cost grows with raw input:
   Clean, chunk, deduplicate, cache, and choose task-appropriate models.
