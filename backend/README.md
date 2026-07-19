# Crowscap Backend

FastAPI backend for Crowscap's source-aware memory engine.

The backend owns the core MemoryAgent behavior: chat routing, capture, extraction, embeddings, semantic retrieval, relationship detection, recall, belief audits, preference learning, user isolation, and MCP tools.

## Responsibilities

- Accept text, URL, YouTube, and PDF captures.
- Classify user intent before committing content to memory.
- Extract typed atomic memories with Qwen Cloud.
- Preserve original sources separately from extracted memory atoms.
- Embed memories for semantic search.
- Detect relationships between new and existing memories.
- Schedule recall and evaluate recall answers.
- Run belief audits over saved memories and public source leads.
- Track explicit and inferred user preferences.
- Archive memories the user no longer wants surfaced.
- Expose read-only memory tools over MCP/SSE.

## Stack

- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL with vector support
- Qwen Cloud through the OpenAI-compatible SDK
- MCP over SSE

## Local Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python scripts/init_db.py
python scripts/run_dev.py
```

Git Bash:

```bash
cd backend
source .venv/Scripts/Activate
python -m pip install -e ".[dev]"
python scripts/init_db.py
python scripts/run_dev.py
```

`scripts/run_dev.py` intentionally starts the app through the project virtual environment. This avoids the common issue where a globally installed `uvicorn` runs without project dependencies such as SQLAlchemy.

Local API docs:

```text
http://127.0.0.1:8000/docs
```

## Environment

Create `.env` from `.env.example`.

Minimum local values:

```text
DATABASE_URL=sqlite:///./crowscap_dev.db
DASHSCOPE_API_KEY=your_qwen_cloud_key
QWEN_BASE_URL=https://your-qwen-workspace-endpoint/compatible-mode/v1
QWEN_FAST_MODEL=qwen-turbo
QWEN_CHAT_MODEL=qwen-plus
QWEN_EXTRACTION_MODEL=qwen-plus
QWEN_RELATIONSHIP_MODEL=qwen-turbo
QWEN_EMBEDDING_MODEL=text-embedding-v4
QWEN_BELIEF_AUDIT_MODEL=qwen-plus
```

Production also requires authentication proxy settings so requests are scoped to the signed-in user:

```text
CROWSCAP_AUTH_REQUIRED=true
CROWSCAP_PROXY_SECRET=shared_secret_between_frontend_and_backend
```

Never commit real secrets.

## Qwen Cloud Integration

The backend uses Qwen Cloud through the OpenAI-compatible API. The main integration file is:

```text
app/ai/qwen_client.py
```

It handles:

- Chat completions.
- JSON mode.
- Embedding generation.
- Embedding batching.
- Model routing.
- Provider-specific error messages.

Structured outputs are always validated with Pydantic. Valid JSON is not treated as valid schema until the backend validates it.

## Memory Pipeline

```text
Capture -> Guard -> Extract -> Embed -> Deduplicate -> Relate -> Schedule -> Persist
```

Important behavior:

- Original source content is stored separately from memory atoms.
- Memory atoms are small units such as claims, principles, warnings, actions, definitions, references, and questions.
- Duplicate captures reuse existing memory where possible.
- Relationship detection skips near-duplicates and low-quality candidate pairs.
- Relationship detection is non-fatal. If Qwen is unavailable, capture can still succeed.
- Recall scheduling begins at capture time.
- Archived memories stop appearing in active search, recall, audits, and nearby context.

## Chat Routing

The chat endpoint uses a hybrid router:

- Deterministic routing for safety-sensitive or stateful actions such as reminders, archiving, factual current-chat questions, and pending URL confirmation.
- Qwen-based classification for open-ended natural language.

This prevents two failure modes:

- Treating every user message as something to save.
- Letting the model guess factual conversation history instead of reading stored messages.

Normal conversation stays normal. Knowledge questions use memory retrieval. Capture requires user intent.

## Context Window Strategy

Crowscap retrieves memory atoms, not whole documents.

Before memories are injected into a chat or audit prompt, the backend:

- Filters for relevance.
- Removes near-duplicate memory context.
- Prioritizes by semantic similarity, confidence, source strength, and recency.
- Keeps memory context within a bounded token budget.
- Compresses older conversation history while preserving recent turns verbatim.

This directly supports the MemoryAgent requirement to recall critical memories within limited context windows.

## Core API Surfaces

```text
GET  /api/v1/health
POST /api/v1/chat
POST /api/v1/search
POST /api/v1/captures/text
POST /api/v1/captures/url
POST /api/v1/captures/pdf
GET  /api/v1/captures/{capture_id}/status
GET  /api/v1/sources/{source_id}
GET  /api/v1/memories/{memory_id}
POST /api/v1/memories/{memory_id}/archive
GET  /api/v1/recalls/due
POST /api/v1/recalls/{memory_id}/answer
POST /api/v1/beliefs/audit
GET  /api/v1/preferences/me
POST /api/v1/preferences/learn-now
```

See the full contract in `../docs/09-api-contract.md`.

## MCP Server

Crowscap exposes read-only memory tools over SSE.

Local run:

```powershell
cd backend
.\.venv\Scripts\python -m app.mcp.server
```

Local SSE URL:

```text
http://127.0.0.1:8010/mcp/sse
```

Production SSE URL:

```text
https://api.crowscap.xyz/mcp/sse
```

Current read-only tools:

- `search_memory`
- `audit_belief`
- `get_due_recalls`
- `get_user_preferences`

The MCP layer delegates to existing backend services. It does not duplicate memory logic.

## Tests

```powershell
cd backend
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m compileall app
```

Useful focused tests:

```powershell
.\.venv\Scripts\python -m pytest tests\test_chat.py
.\.venv\Scripts\python -m pytest tests\test_captures.py
.\.venv\Scripts\python -m pytest tests\test_ingestion.py
.\.venv\Scripts\python -m pytest tests\test_mcp_tools.py
```

## Deployment

The backend is deployed on Alibaba Cloud ECS behind Nginx:

```text
https://api.crowscap.xyz
```

Health check:

```text
https://api.crowscap.xyz/api/v1/health
```

Deployment notes:

- `../docs/14-alibaba-ecs-deployment.md`
- `../docs/16-ecs-mcp-deployment.md`

## Design Principle

The backend should never pretend that memory is the same as truth.

It stores what the user saved, tracks where it came from, exposes confidence and uncertainty, and helps the user revisit ideas with better context.
