# Roadmap and Skills

Current date: 2026-06-11.
Submission deadline: 2026-07-09 at 10:00 PM WAT.



## Phase 0: Setup and Qwen First Call

Target: June 11-12.

Deliverables:
- Repository structure.
- `.env.example`.
- Backend skeleton.
- Frontend skeleton.
- Qwen Cloud first API call from backend.
- Structured output smoke test.
- Embedding smoke test.

Skills:
- Git/GitHub.
- Python virtual environments.
- Node/npm.
- Environment variables.
- OpenAI-compatible SDK.
- Qwen API key management.

## Phase 1: Ingestion Foundation

Target: June 13-17.

Deliverables:
- Capture API.
- Source/capture database tables.
- Background job queue.
- Plain text extraction.
- Article URL extraction with safety checks.
- PDF extraction.
- YouTube transcript MVP if transcript is available.
- Processing status endpoint.

Skills:
- FastAPI routing.
- Pydantic request/response models.
- SQLAlchemy models.
- Alembic migrations.
- Celery workers.
- Redis.
- URL security and SSRF protection.
- HTML extraction.
- PDF text extraction.

## Phase 2: Atomic Memory Extraction

Target: June 18-22.

Deliverables:
- Qwen prompt for capture intent classification.
- Qwen prompt for atomic memory extraction.
- Pydantic schemas for model output.
- JSON validation and repair flow.
- Memory table and embedding storage.
- Frontend capture/inbox/memory views.

Skills:
- Prompt engineering.
- Structured JSON output.
- Pydantic validation.
- Token management.
- Embeddings.
- React components.
- TanStack Query.
- Tailwind layout.

## Phase 3: Relations, Recall, and Audit

Target: June 23-29.

Deliverables:
- Vector search over memories.
- Relation/tension detection.
- Multi-signal recall scoring.
- Recall prompt generation.
- Recall answer flow.
- Knowledge Audit API.
- Explicit user preference profile.
- Preference-aware chat, recall, and audit behavior.
- Audit frontend page.

Skills:
- Vector similarity.
- Retrieval ranking.
- Relation classification.
- Recall algorithms.
- Product thinking.
- Preference modeling.
- Source-grounded synthesis.
- UX for uncertainty.

## Phase 4: MCP, Evaluation, and Deployment

Target: June 30-July 5.

Deliverables:
- MCP server with memory tools.
- Evaluation harness comparing naive RAG vs Crowscap atomic retrieval.
- Docker setup.
- Alibaba Cloud backend deployment.
- OSS or Alibaba Cloud service usage proof file.
- Architecture diagram.
- README installation instructions.

Skills:
- MCP tool design.
- Qwen Responses API MCP integration.
- Docker.
- Alibaba Cloud ECS or container deployment.
- Object storage APIs.
- Evaluation metrics.
- Technical documentation.

## Phase 5: Demo and Submission Polish

Target: July 6-9.

Deliverables:
- Seed demo dataset.
- Scripted demo route.
- Public repo cleanup.
- LICENSE.
- Final architecture diagram.
- Devpost text description.
- Demo video less than 3 minutes.
- Deployment proof recording or link as required.
- Optional blog/social post.

Skills:
- Demo storytelling.
- Video recording.
- Technical writing.
- QA.
- Bug triage.
- Time management.

## Core Skills by Area

Frontend:
- TypeScript.
- React component composition.
- Next.js App Router.
- Tailwind CSS.
- TanStack Query.
- Form UX.
- Responsive design.
- State and loading/error handling.

Backend:
- Python.
- FastAPI.
- Pydantic v2.
- SQLAlchemy 2.x.
- Alembic.
- Celery.
- Redis.
- PostgreSQL.
- Vector search.
- API design.
- Testing.

AI:
- Qwen Cloud API.
- Structured outputs.
- Embeddings.
- Reranking.
- Prompt design.
- JSON validation/repair.
- Retrieval-augmented generation.
- Evaluation harnesses.

Security:
- SSRF prevention.
- Upload validation.
- Rate limiting.
- Secrets management.
- User data privacy.
- Safe error handling.

Product:
- Memory lifecycle design.
- Capture intent modeling.
- Tension detection language.
- Familiarity without mastery.
- Knowledge audits.
- Preference learning without over-inferring.
- Demo narrative.

## Learning Priority 

Highest personal learning leverage:

1. Make Qwen API calls personally.
2. Understand structured output and malformed JSON handling.
3. Understand embeddings vs reranking.
4. Understand the memory data model.
5. Understand the demo story and product promise.

