# Alibaba PostgreSQL Migration Runbook

This is the production database path for Crowscap.

Local development can stay on SQLite. Alibaba deployment should use PostgreSQL with pgvector so semantic memory search is indexed inside the database instead of scanning JSON vectors in Python.

## Why This Matters For The Hackathon

Crowscap is a MemoryAgent. The database is part of the product architecture, not just storage.

PostgreSQL on Alibaba gives us:

- durable relational storage for sources, captures, memories, recalls, relationships, conversations, and audit outputs
- pgvector search for semantic memory retrieval
- a clear Alibaba Cloud deployment story for judging
- one database instead of a separate vector database service

## What Must Be True Before Switching

Before pointing the app at PostgreSQL:

1. Qwen extraction, embeddings, search, recall, chat, URL, YouTube, PDF, and belief audit should work locally.
2. Alembic migrations must create the cloud schema.
3. `pgvector` support must be verified on the selected Alibaba database SKU.
4. Existing SQLite memories should be migrated only after the cloud schema is verified.
5. The backend must not auto-create production tables at startup. Production schema changes go through Alembic.

The code now follows that rule:

- SQLite: `Base.metadata.create_all()` is allowed for smooth local development.
- PostgreSQL: Alembic owns table creation; startup only verifies/repairs the pgvector column and index if tables already exist.

## Alibaba Links

Use these links while setting up the cloud database:

- Alibaba Cloud Console: https://homenew.console.aliyun.com/
- RDS console: https://rds.console.aliyun.com/
- RDS PostgreSQL create-instance docs: https://www.alibabacloud.com/help/en/rds/apsaradb-rds-for-postgresql/create-an-apsaradb-rds-for-postgresql-instance
- IP whitelist docs: https://www.alibabacloud.com/help/en/rds/apsaradb-rds-for-postgresql/configure-an-ip-address-whitelist-for-an-apsaradb-rds-for-postgresql-instance
- Connect to RDS PostgreSQL docs: https://www.alibabacloud.com/help/en/rds/apsaradb-rds-for-postgresql/connect-to-an-apsaradb-rds-for-postgresql-instance
- Endpoint and port docs: https://www.alibabacloud.com/help/en/rds/apsaradb-rds-for-postgresql/view-and-change-the-endpoints-and-port-numbers-of-an-apsaradb-rds-for-postgresql-instance

## Alibaba RDS Setup, Click By Click

### 1. Open The RDS Console

1. Go to https://rds.console.aliyun.com/
2. Make sure the region selector is set to the region you want.
3. For Crowscap, prefer the same region as the backend deployment.
4. If your Qwen workspace is in Singapore / `ap-southeast-1`, use Singapore for the database too if the price and availability are acceptable.

Why:
Keeping Qwen, backend, and database close reduces latency and gives the hackathon story a cleaner Alibaba architecture.

### 2. Create A PostgreSQL Instance

In the RDS console:

1. Click `Create Instance`.
2. Choose `PostgreSQL`.
3. Choose PostgreSQL 15 or 16 if available.
4. Choose a small paid or trial-friendly instance class for the hackathon.
5. Choose storage that is enough for demo usage. Even 20 GB is more than enough for now.
6. Choose the same VPC that your Alibaba backend/ECS will use.
7. Choose the same zone as the backend if possible.
8. Set network type to VPC.
9. Enable SSL if Alibaba offers it during setup. If not, enable it after creation.
10. Confirm and create the instance.

Recommended Crowscap values:

| Setting | Recommended value |
| --- | --- |
| Engine | PostgreSQL |
| Version | 15 or 16 |
| Region | Same as backend/Qwen workspace if practical |
| Database name | `crowscap` |
| App account | `crowscap_app` |
| Port | `5432` |
| Network | VPC/internal for deployment, public only for local testing |
| SSL | Required for public connections |

### 3. Wait Until The Instance Is Running

1. Go to the RDS instance list.
2. Open the new PostgreSQL instance.
3. Wait until status is `Running`.
4. Copy the instance ID somewhere safe for the deployment proof recording.

### 4. Create The Database

Inside the RDS instance:

1. Open the `Databases` section.
2. Click `Create Database`.
3. Database name: `crowscap`
4. Character set: `UTF8`
5. Collation: keep Alibaba default unless the console asks for a specific value.
6. Save.

### 5. Create The App Account

Inside the same RDS instance:

1. Open `Accounts`.
2. Click `Create Account`.
3. Account name: `crowscap_app`
4. Account type: normal/standard privileged app user, not root/super admin.
5. Set a strong password.
6. Grant access to the `crowscap` database.
7. Give read/write privileges needed by the app.

Keep this password out of Git. It goes only in `.env` or Alibaba deployment environment variables.

### 6. Configure Network Access

For deployed backend:

1. Put the backend and RDS instance in the same VPC if possible.
2. Use the internal RDS endpoint.
3. Add the backend ECS/private IP or security group to the RDS whitelist.

For local laptop testing:

1. Temporarily enable or copy the public endpoint.
2. Add your current public IP to the RDS whitelist.
3. Remove your public IP later when the demo deployment is stable.

Do not use `0.0.0.0/0` unless you are debugging for a minute and immediately remove it. It is unsafe.

### 7. Get The Endpoint

Inside the RDS instance:

1. Open `Database Connection` or `Endpoints`.
2. Copy the internal endpoint for Alibaba deployment.
3. Copy the public endpoint only if you need local testing from your machine.
4. Confirm the port is `5432`.

Your final backend URL shape should look like:

```env
DATABASE_URL=postgresql+psycopg://crowscap_app:replace-password@replace-host:5432/crowscap?sslmode=require
```

Example shape only:

```env
DATABASE_URL=postgresql+psycopg://crowscap_app:MySecretPassword@pgm-xxxx.pg.rds.aliyuncs.com:5432/crowscap?sslmode=require
```

### 8. Verify pgvector Support

Connect to the database using Alibaba Cloud DMS, DataGrip, TablePlus, pgAdmin, or `psql`.

Run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Expected result:

```text
vector
```

If this fails because the selected Alibaba PostgreSQL SKU does not expose pgvector, do not panic. The app still has the JSON embedding fallback, but production-grade search should use one of these paths:

- switch to an Alibaba PostgreSQL-compatible product/SKU that supports the `vector` extension
- run PostgreSQL with pgvector on ECS for the demo
- temporarily deploy with JSON fallback and document pgvector as the intended production migration

For the hackathon, the strongest story is RDS/PolarDB-compatible PostgreSQL with `vector` enabled.

### 9. Put The Database URL In Backend `.env`

On your local machine:

```powershell
cd "C:\Users\USER\Desktop\Startups\new project\crowscap\backend"
```

Edit `.env`:

```env
DATABASE_URL=postgresql+psycopg://crowscap_app:replace-password@replace-host:5432/crowscap?sslmode=require
```

Keep this line local. Do not commit it.

### 10. Run The Migration

From `backend`:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

This creates:

- conversations
- chat messages
- sources
- captures
- memories
- recall reviews
- memory relations
- pgvector column and HNSW index

### 11. Verify From Our App

Run:

```powershell
.\.venv\Scripts\python.exe scripts\check_postgres.py
```

Expected:

```text
database_dialect=postgresql
pgvector_extension=True
memories_table=True
embedding_vector_column=True
embedding_vector_hnsw_index=True
postgres_ready=True
```

### 12. Migrate Local SQLite Memories

Only do this after `postgres_ready=True`.

```powershell
$env:SQLITE_DATABASE_URL="sqlite:///./crowscap_dev.db"
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py
```

Then backfill pgvector:

```powershell
.\.venv\Scripts\python.exe scripts\backfill_pgvector.py
```

### 13. Start Backend Against Alibaba PostgreSQL

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Look for logs like:

```text
db.connected status=ok url=postgresql+psycopg://...
db.vector.ready extension=vector column=memories.embedding_vector
```

### 14. Test The Product Flow

In the frontend:

1. Capture a short text note.
2. Search for it semantically.
3. Ask for a belief audit.
4. Confirm the backend logs show `search.pgvector_complete`.

That log confirms Crowscap is using pgvector search instead of local JSON scanning.

## Environment Variables

Local SQLite:

```env
DATABASE_URL=sqlite:///./crowscap_dev.db
```

Alibaba PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://crowscap_app:replace-password@replace-host:5432/crowscap?sslmode=require
```

If you are migrating existing local data:

```env
SQLITE_DATABASE_URL=sqlite:///./crowscap_dev.db
```

Never commit the real database password.

## Commands

Run from `backend`.

Install dependencies if needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Apply PostgreSQL schema:

```powershell
$env:DATABASE_URL="postgresql+psycopg://crowscap_app:replace-password@replace-host:5432/crowscap?sslmode=require"
.\.venv\Scripts\alembic.exe upgrade head
```

Verify the cloud database:

```powershell
.\.venv\Scripts\python.exe scripts\check_postgres.py
```

Expected successful output:

```text
database_dialect=postgresql
pgvector_extension=True
memories_table=True
embedding_vector_column=True
embedding_vector_hnsw_index=True
postgres_ready=True
```

Migrate local SQLite data into PostgreSQL:

```powershell
$env:SQLITE_DATABASE_URL="sqlite:///./crowscap_dev.db"
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py
```

Backfill vector columns from stored JSON embeddings:

```powershell
.\.venv\Scripts\python.exe scripts\backfill_pgvector.py
```

Run backend against PostgreSQL:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## What The Migration Creates

The first PostgreSQL migration creates:

- `conversations`
- `chat_messages`
- `sources`
- `captures`
- `memories`
- `recall_reviews`
- `memory_relations`

The `memories` table stores embeddings in two forms:

- `embedding_json`: portable fallback used by SQLite and tests
- `embedding_vector vector(1024)`: PostgreSQL pgvector search column

It also creates:

```sql
CREATE INDEX ix_memories_embedding_vector_hnsw
ON memories USING hnsw (embedding_vector vector_cosine_ops)
WHERE embedding_vector IS NOT NULL;
```

That is the production search accelerator.

## Search Runtime Behavior

At runtime, semantic search behaves like this:

1. Embed the user query with Qwen `text-embedding-v4`.
2. If the active database is PostgreSQL and `embedding_vector` is available, use pgvector cosine search.
3. If pgvector is not available, fall back to Python cosine search over `embedding_json`.

This means:

- local development remains easy
- PostgreSQL deployment is faster and more scalable
- a broken pgvector setup does not take down the entire app

## MCP Timing

MCP should wrap stable capabilities, not unstable internals.

Do PostgreSQL first because the MCP tools need reliable contracts:

- `capture_memory`
- `search_memory`
- `get_due_recalls`
- `audit_belief`
- `get_source`

Once Postgres is stable, MCP becomes a clean external interface over tools that already work.

## Deployment Proof Angle

For the hackathon submission, capture a short proof video showing:

1. Alibaba ECS or app service running the backend.
2. `DATABASE_URL` pointing to Alibaba PostgreSQL without exposing secrets.
3. `scripts/check_postgres.py` returning `postgres_ready=True`.
4. A live request from the frontend triggering search/audit against the deployed backend.

That demonstrates real Alibaba Cloud usage beyond just calling Qwen.
