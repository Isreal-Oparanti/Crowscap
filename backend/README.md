# Crowscap Backend

FastAPI backend for Crowscap.

## Local Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload
```

Git Bash users can activate and run scripts with forward slashes:

```bash
source .venv/Scripts/Activate
python scripts/init_db.py
uvicorn app.main:app --reload
```

Recommended development command:

```bash
python scripts/run_dev.py
```

`run_dev.py` automatically switches to `backend/.venv` even if the shell was not
activated. This prevents a globally installed `uvicorn` from starting with a Python
environment that is missing SQLAlchemy or other project dependencies.

Open the API docs in a browser:

```text
http://127.0.0.1:8000/docs
```

### `ModuleNotFoundError: No module named 'sqlalchemy'`

This means the command resolved to the global Python installation instead of
`backend/.venv`. Either activate the environment:

```bash
source .venv/Scripts/Activate
python -m uvicorn app.main:app --reload
```

Or use the safer launcher:

```bash
python scripts/run_dev.py
```

Default local database:

```text
sqlite:///./crowscap_dev.db
```

This keeps Phase 0 smooth. The same SQLAlchemy app configuration accepts a Postgres URL later:

```text
postgresql+psycopg://user:password@localhost:5432/crowscap
```

For Alibaba PostgreSQL and pgvector setup, see `../docs/13-alibaba-postgres-migration.md`.

## Qwen Smoke Test

Set `DASHSCOPE_API_KEY` in `.env`, then run:

```powershell
python scripts/qwen_smoke.py
```

The script uses Qwen Cloud's OpenAI-compatible endpoint:

```text
https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

## First Capture Endpoint

Once the server is running, open Swagger:

```text
http://127.0.0.1:8000/docs
```

Then test:

```text
POST /api/v1/captures/text
```

Request body:

```json
{
  "content": "A founder should not wait until launch to think about distribution. They should test channels early, learn which path reaches customers, and use those lessons to shape the product instead of treating distribution as a later marketing task.",
  "intent_text": "remember and apply this to my startup",
  "user_note": "I keep hearing distribution matters but I want to actually use it.",
  "source_title": "Distribution learning note"
}
```

Or send with curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/captures/text \
  -H "Content-Type: application/json" \
  -d '{"content":"A founder should not wait until launch to think about distribution. They should test channels early, learn which path reaches customers, and use those lessons to shape the product instead of treating distribution as a later marketing task.","intent_text":"remember and apply this to my startup","user_note":"I keep hearing distribution matters but I want to actually use it.","source_title":"Distribution learning note"}'
```

Without `DASHSCOPE_API_KEY`, this endpoint returns a clear 503 instead of pretending extraction worked.

Current behavior:
- `content` accepts 20 to 10,000 characters.
- `intent_text`, `user_note`, and `source_title` are optional context, not required tags.
- the backend normalizes common model label variants such as `Compare`, `watch-later`, or `Factual Claim`.
- the backend repairs known cross-field taxonomy mistakes, such as Qwen placing
  `intention` in `epistemic_label` instead of using it as `memory_type`.
- if deterministic normalization is not enough, extraction performs one bounded
  schema-repair call before returning a friendly validation error.
- longer sources will use a future document upload/chunking endpoint.
- duplicate text captures reuse existing memories by content hash and skip a new Qwen call.
- the exact submitted text is stored on the source and returned as `original_content`; atomic memories never replace the source-of-record.
- `GET /api/v1/sources/{source_id}` returns the original capture for chat and recall reference views.
- extraction uses Qwen JSON mode with temperature `0` for more deterministic structured output.
- each new memory is embedded through Qwen and stored in `embedding_json` for local SQLite development.
- on PostgreSQL, the same embedding is also written to `memories.embedding_vector` for pgvector search.
- duplicate captures with old unembedded memories will backfill missing embeddings before returning.
- duplicate captures from older development runs will backfill missing relationship scans once, then mark the source as scanned.
- responses show `embedding_dimensions` to confirm embedding happened without returning the full vector.
- relationship detection runs after embedding: nearby older memories are classified as `confirms`, `conflicts`, `tension`, `extends`, or `qualifies`.
- relationship detection skips meta memories such as `intention`, `question`, and `reference`.
- relationship detection also skips meta memories as older candidates, and skips very high-similarity near-duplicates.
- relationship detection batches eligible memories into one Qwen call per capture.
- relationship detection caps total pairs per capture and fails fast because it is useful but non-critical.
- relationship candidates default to a calibrated `0.50` similarity floor for `text-embedding-v4`.
- Qwen must cite exact phrases from both memories; weak or ungrounded classifications are discarded.
- relationship detection is non-fatal; if Qwen cannot classify relationships, capture still succeeds and the skip is logged.

## Conversational Chat Endpoint

The frontend sends every chat turn to the backend instead of guessing from punctuation.

```text
POST /api/v1/chat
```

The backend chooses one action:

- `acknowledge`: respond normally and create no memory.
- `capture`: run extraction, embeddings, deduplication, relationships, and scheduling.
- `answer`: retrieve relevant memories and synthesize a source-aware response.

Memory answers lead with a direct synthesis, then return supporting evidence,
knowledge gaps, context-dependent tensions, and a useful next action or question.
Short acknowledgements such as `okay`, `thanks`, `got it`, and `this makes sense`
are handled without creating memory.

## Semantic Search Endpoint

Search embeds the query with the same Qwen embedding model used for memories, then ranks memories by cosine similarity.

```text
POST /api/v1/search
```

Request body:

```json
{
  "query": "how do I get my product to customers",
  "limit": 10,
  "min_score": 0.25,
  "include_archived": false
}
```

Current local behavior:
- SQLite stores vectors as JSON.
- Python computes cosine similarity.
- Results include memory content, type, epistemic label, confidence, source strength, source title, similarity score, and embedding dimensions.
- Responses include `candidate_count`, `embedded_candidate_count`, `returned_count`, and `top_score` so we can tune thresholds empirically.
- Postgres/pgvector will replace only the similarity lookup later; query embedding and response shape stay the same.

## Recall Endpoint

Every new memory receives an initial review schedule:

- high confidence: 24 hours later
- medium confidence: 12 hours later
- low or unknown confidence: 6 hours later

Existing local SQLite memories are backfilled as due when the schema upgrades, so the endpoint has useful development data immediately.

```text
GET /api/v1/recalls/due
```

Optional query:

```text
GET /api/v1/recalls/due?limit=10
```

Current behavior:
- returns active memories where `next_review_at` is in the past.
- orders by most overdue first.
- includes source title, recall score, review count, and relationship context.
- includes a prompt selected from memory type, source strength, and tensions.
- warns when an idea is advice, opinion, or weakly evidenced rather than a verified fact.

Submit a recall answer:

```text
POST /api/v1/recalls/{memory_id}/answer
```

The response includes persisted evaluation feedback, an understanding summary,
knowledge gaps, context to consider, a deeper follow-up question, and the next
scheduled review.

## Local MCP Server

Crowscap now exposes a read-only MCP server over SSE. This lets an agent call the
memory system as tools without duplicating backend logic.

Run it from the backend folder:

```powershell
.\.venv\Scripts\python -m app.mcp.server
```

Default local SSE URL:

```text
http://127.0.0.1:8010/mcp/sse
```

Read-only tools currently exposed:

- `search_memory`: semantic search over saved memories.
- `audit_belief`: synthesize what saved memories appear to say about a topic.
- `get_due_recalls`: return due knowledge recalls and one-time reminders.
- `get_user_preferences`: return the learned preference profile.

Verify the tool output contracts:

```powershell
.\.venv\Scripts\python -m pytest tests\test_mcp_tools.py
```

The MCP contract lives in `../docs/15-mcp-contract.md`.

## What DASHSCOPE_API_KEY Means

`DASHSCOPE_API_KEY` is the Alibaba/Qwen Cloud API key. The backend uses it to call Qwen models through the OpenAI-compatible API. It lives only in `.env`; never commit it.

Create `.env` from `.env.example` and fill in:

```text
DASHSCOPE_API_KEY=your_real_qwen_cloud_key_here
QWEN_BASE_URL=https://your-openai-compatible-endpoint/compatible-mode/v1
QWEN_REASONING_MODEL=qwen3.7-plus
QWEN_FAST_MODEL=qwen-turbo
QWEN_CHAT_MODEL=qwen-plus
QWEN_EXTRACTION_MODEL=qwen-plus
QWEN_RELATIONSHIP_MODEL=qwen-turbo
```

Use the **OpenAI Compatible Endpoint** from your Qwen Cloud workspace for `QWEN_BASE_URL`.
For the hackathon workspace, the endpoint may look like:

```text
https://ws-your-workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
```

Do not use the DashScope `/api/v1` endpoint with the OpenAI SDK. The backend is using the OpenAI-compatible SDK path.

Model routing:
- `qwen3.7-plus` stays reserved for deep reasoning features like belief audits.
- `qwen-plus` handles conversational synthesis and recall evaluation.
- `qwen-plus` is the default extraction model because extraction quality matters.
- `qwen-turbo` is the default relationship model because tension detection is a fast classification task.

## Console Logs

When the server starts and requests run, the terminal prints logs like:

```text
🚀 app.start name=Crowscap API env=development api_prefix=/api/v1
🧠 qwen.configured status=True base_url=https://dashscope-intl.aliyuncs.com/compatible-mode/v1 fast_model=qwen3.6-flash
🗄️ db.connected status=ok url=sqlite:///./crowscap_dev.db
📥 capture.text.start chars=227 intent_present=True note_present=True
🤖 qwen.request mode=json model=qwen3.6-flash prompt_chars=2288
✅ qwen.response_ok mode=json model=qwen3.6-flash chars=942 keys=['inferred_intents', 'memories', 'source_title']
✅ extraction.validated memories=3 intents=['remember', 'apply'] title=Distribution learning note
📊 relationship.candidates memory_id=... scores=[...]
✅ relationship.scan.complete created=1
💾 capture.text.saved source_id=... capture_id=... memories=3 relationships=1
```

## Docs

- ../docs/04-backend-architecture.md
- ../docs/06-memory-engine.md
- ../docs/07-ingestion-and-extraction.md
- ../docs/08-data-model.md
- ../docs/09-api-contract.md
- ../docs/10-security-cost-reliability.md
