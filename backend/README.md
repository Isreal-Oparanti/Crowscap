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

Open the API docs in a browser:

```text
http://127.0.0.1:8000/docs
```

Default local database:

```text
sqlite:///./crowscap_dev.db
```

This keeps Phase 0 smooth. The same SQLAlchemy app configuration accepts a Postgres URL later:

```text
postgresql+psycopg://user:password@localhost:5432/crowscap
```

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
- longer sources will use a future document upload/chunking endpoint.
- duplicate text captures reuse existing memories by content hash and skip a new Qwen call.
- extraction uses Qwen JSON mode with temperature `0` for more deterministic structured output.
- each new memory is embedded through Qwen and stored in `embedding_json` for local SQLite development.
- duplicate captures with old unembedded memories will backfill missing embeddings before returning.
- responses show `embedding_dimensions` to confirm embedding happened without returning the full vector.
- relationship detection runs after embedding: nearby older memories are classified as `confirms`, `conflicts`, `tension`, `extends`, or `qualifies`.
- relationship detection skips meta memories such as `intention`, `question`, and `reference`.
- relationship detection batches eligible memories into one Qwen call per capture.
- relationship detection is non-fatal; if Qwen cannot classify relationships, capture still succeeds and the skip is logged.

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

## What DASHSCOPE_API_KEY Means

`DASHSCOPE_API_KEY` is the Alibaba/Qwen Cloud API key. The backend uses it to call Qwen models through the OpenAI-compatible API. It lives only in `.env`; never commit it.

Create `.env` from `.env.example` and fill in:

```text
DASHSCOPE_API_KEY=your_real_qwen_cloud_key_here
QWEN_BASE_URL=https://your-openai-compatible-endpoint/compatible-mode/v1
QWEN_FAST_MODEL=qwen3.7-plus
QWEN_REASONING_MODEL=qwen3.7-plus
```

Use the **OpenAI Compatible Endpoint** from your Qwen Cloud workspace for `QWEN_BASE_URL`.
For the hackathon workspace, the endpoint may look like:

```text
https://ws-your-workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
```

Do not use the DashScope `/api/v1` endpoint with the OpenAI SDK. The backend is using the OpenAI-compatible SDK path.

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
