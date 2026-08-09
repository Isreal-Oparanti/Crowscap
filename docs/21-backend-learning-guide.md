# Crowscap Backend Learning Guide

This guide explains the Crowscap backend from two angles.

First, the technical architecture: what technologies and backend ideas the project uses, why they exist, and when you would use similar ideas in other systems.

Second, the essential code-level flow: how the actual files in this repository work together when a user chats, saves a link, searches memory, receives recall, signs in, or uses MCP.

The goal is not only to explain Crowscap. The goal is to make the backend concepts reusable in interviews, future jobs, and future products.

## Section 1: Technical Architecture, Techniques, Technologies, And Why

### The Backend In One Sentence

The Crowscap backend is the system that turns user input into durable, searchable, source-aware memory.

The frontend is the interface. The backend is the memory engine.

When a user says:

```text
This video will help my YC application https://youtu.be/...
```

the backend decides what the user is trying to do, saves the source, extracts useful information where possible, creates atomic memory records, embeds those records for semantic search, schedules future recall, and returns a response the user can trust.

### The Core Product Loop

Crowscap is built around a memory lifecycle:

```text
Capture -> Extract -> Structure -> Embed -> Relate -> Recall -> Review -> Adapt
```

Each step has a specific job.

Capture:
- Receive the user's note, link, PDF, video, reminder, or chat instruction.
- Preserve the source and the user's intent.

Extract:
- Read the content when possible.
- Examples: article text, PDF text, YouTube metadata, YouTube captions.

Structure:
- Ask Qwen to turn messy content into memory atoms.
- A memory atom is one useful idea, claim, question, warning, action, reference, or intention.

Embed:
- Convert each memory atom into a vector.
- A vector is a numeric representation of meaning.

Relate:
- Compare new memories with older memories.
- Store useful relationships like conflict, confirmation, extension, or qualification.

Recall:
- Decide what should come back later.
- This is where Crowscap becomes more than storage.

Review:
- Let the user mark memories as useful, done, not now, archived, or deleted.

Adapt:
- Learn user preferences and behavior over time.
- Use that to improve routing, recall, notification tone, and memory selection.

### Runtime Architecture

The current backend runtime has these main parts:

```text
Client apps
  Web frontend
  Mobile app
  MCP clients

Backend API
  FastAPI routes
  Auth dependency
  Rate limiter
  Chat router
  Capture pipeline
  Search and recall services
  Notification services

Storage
  PostgreSQL / Neon / Alibaba-compatible Postgres target
  SQLAlchemy ORM
  Alembic migrations

AI services
  Qwen chat models
  Qwen JSON extraction
  Qwen embeddings
  Qwen relationship checks
  Qwen recall and audit synthesis

External extractors
  HTTP article extraction
  YouTube Data API metadata
  yt-dlp captions
  PyMuPDF PDF extraction

Delivery
  Server-Sent Events for live in-app updates
  Web Push for PWA notifications
  Expo push for mobile notifications
  MCP over SSE for external AI agents
```

### Why FastAPI

Crowscap uses FastAPI because it gives a clean way to expose typed HTTP APIs in Python.

FastAPI gives us:
- Route definitions like `POST /api/v1/chat`.
- Request validation through Pydantic models.
- Response models for API consistency.
- Dependency injection for shared things like database sessions and authenticated users.
- Automatic OpenAPI docs at `/docs`.

In this project, FastAPI lives mostly in:

```text
backend/app/main.py
backend/app/api/v1/
```

Example idea:

```python
@router.post("/chat", response_model=ChatResponse)
def chat(...):
    return process_chat_message(...)
```

That means:
- The route receives HTTP.
- FastAPI validates the request body.
- Dependencies resolve the database session and current user.
- The service layer does the actual business logic.
- FastAPI serializes the response.

### Why Uvicorn And ASGI

FastAPI runs on ASGI. ASGI is the Python standard for async web servers.

Uvicorn is the server process that actually listens on a port and serves the FastAPI app.

On the server, systemd runs something like:

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Nginx sits in front of Uvicorn and exposes the public domain:

```text
https://api.crowscap.xyz -> nginx -> uvicorn -> FastAPI
```

Why this matters:
- Uvicorn handles the Python app.
- Nginx handles TLS, public routing, buffering, and reverse proxying.
- Keeping Uvicorn on `127.0.0.1` means the app is not directly open to the internet.

### Why Pydantic

Pydantic is used for validation and structured data.

It appears in:

```text
backend/app/schemas/
backend/app/core/config.py
backend/app/ai/structured_outputs.py
```

Crowscap uses Pydantic for three kinds of validation.

API validation:
- Is the request body shaped correctly?
- Does a field meet minimum length?
- Is a URL field actually a string?

Settings validation:
- Load environment variables from `.env`.
- Convert values to the right type.
- Keep secrets as `SecretStr`.

AI output validation:
- Qwen can be asked to return JSON, but JSON alone is not enough.
- Pydantic checks if the model returned the required fields.
- If Qwen returns malformed or incomplete structure, the backend can repair or reject it.

This is important in AI systems because model output is probabilistic. You cannot trust it like normal code output.

### Why SQLAlchemy

SQLAlchemy is the ORM.

ORM means Object Relational Mapper.

In simple terms:

```text
Python object <-> database row
```

Instead of writing raw SQL everywhere, the code can work with models:

```python
memory = Memory(content="...")
db.add(memory)
db.commit()
```

SQLAlchemy turns that into SQL inserts.

Crowscap uses SQLAlchemy because:
- The app has many related tables.
- User data must be queried safely.
- Relationships between sources, captures, memories, reminders, and users matter.
- Transactions are needed so partial saves do not corrupt memory state.

The main model file is:

```text
backend/app/db/models.py
```

The session setup is:

```text
backend/app/db/session.py
```

### What A Database Session Is

A database session is a unit of work.

Think of it as the backend's current conversation with the database.

In Crowscap:

```python
db.add(source)
db.add(capture)
db.add(memory)
db.commit()
```

`commit()` means:

```text
Make all of these changes permanent.
```

If something fails before commit, the backend can roll back and avoid saving half of a capture.

This matters for Crowscap because a save operation is not one database row. It can include:
- Source row
- Capture row
- Several memory rows
- Embeddings
- Relationships
- Perspective notes
- Recall schedules

### Why Alembic

Alembic manages database migrations.

A migration is a versioned change to the database schema.

Examples:
- Add a `users` table.
- Add a `source_type` column.
- Add a `push_subscriptions` table.
- Add an index for faster lookup.

Without migrations, every developer or server would need to manually edit the database. That becomes dangerous quickly.

Typical command:

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
```

On Linux server:

```bash
.venv/bin/alembic upgrade head
```

The important principle:

```text
Code and database schema must move together.
```

### Why PostgreSQL

Crowscap uses a relational database because memory is not just text blobs.

The product needs structured relationships:
- A user owns conversations.
- A conversation has chat messages.
- A source has captures.
- A capture creates memories.
- A memory belongs to a source.
- A memory can have relationships with other memories.
- A memory can be recalled, reviewed, archived, or deleted.
- A user can have push subscriptions.

PostgreSQL is a strong default because:
- It is reliable.
- It handles relational data well.
- It supports JSON fields.
- It can support vector search through pgvector or equivalent vector operations.

### What Embeddings Are

An embedding is a list of numbers that represents the meaning of text.

Example:

```text
"How to sell as a startup founder"
```

gets converted into something like:

```text
[0.012, -0.44, 0.81, ...]
```

The actual vector can have hundreds or thousands of dimensions.

Why this matters:

Keyword search only matches words.

Semantic search matches meaning.

If the user asks:

```text
What do I know about getting users?
```

Crowscap should find memories about:
- distribution
- sales
- customer discovery
- launch strategy
- founder-led selling

even if the exact phrase "getting users" is not in the memory.

Embeddings are generated in:

```text
backend/app/services/embedding_service.py
backend/app/ai/qwen_client.py
```

### Why Qwen Cloud

Qwen Cloud powers the AI-heavy parts of the backend.

Crowscap uses Qwen for:
- Intent routing.
- Chat responses.
- Structured memory extraction.
- Embeddings.
- Relationship classification.
- Belief audits.
- Recall evaluation.
- Notification copy generation.

The central client is:

```text
backend/app/ai/qwen_client.py
```

It uses Qwen's OpenAI-compatible API style, which means the code can call Qwen using an SDK interface similar to OpenAI's:

```python
client.chat.completions.create(...)
client.embeddings.create(...)
```

Why this architecture is useful:
- Business logic does not directly know HTTP details.
- Model names are configured through environment variables.
- Errors can be normalized in one place.
- JSON and embedding calls are separated cleanly.

### Why JSON Mode Is Not Enough

Qwen can be asked to return JSON.

But valid JSON does not mean valid business data.

For example, this is valid JSON:

```json
{"memories": "yes"}
```

But the backend needs something more specific:

```json
{
  "memories": [
    {
      "memory_type": "claim",
      "content": "Founder-led selling is learning, not only pitching.",
      "confidence": "high"
    }
  ]
}
```

That is why Crowscap validates Qwen output with Pydantic after the model responds.

The pattern is:

```text
Ask Qwen for JSON -> parse JSON -> validate schema -> repair once if needed -> fail gracefully if still invalid
```

This is a core AI backend principle:

```text
LLMs can generate structure, but your backend must enforce structure.
```

### What RAG Means

RAG means Retrieval Augmented Generation.

It has two steps:

1. Retrieve relevant stored information.
2. Give that retrieved information to the model before it answers.

Without RAG:

```text
User asks: What do I know about distribution?
Model guesses from general knowledge.
```

With RAG:

```text
User asks: What do I know about distribution?
Backend searches the user's memories.
Backend sends relevant memories to Qwen.
Qwen answers using those memories.
```

Crowscap's retrieval layer is in:

```text
backend/app/services/search_service.py
backend/app/services/chat_service.py
backend/app/services/recall_service.py
```

### Why Atomic Memories Instead Of Whole Documents

Naive RAG often stores and retrieves large chunks of documents.

Crowscap stores atomic memories.

Example article:

```text
Long article about startup sales, pricing, customer calls, positioning, and founder psychology.
```

Naive RAG might retrieve a 1500-word chunk.

Crowscap extracts smaller memory atoms:

```text
Founder-led sales is also customer discovery.
Early customers buy outcomes, not features.
Pricing objections reveal perceived value gaps.
```

Why this is better:
- Search becomes more precise.
- Context windows stay smaller.
- Recall can target one useful idea.
- Conflicts between ideas become easier to detect.
- The model has less irrelevant text to wade through.

### What Context Window Management Means

Every LLM call has a maximum amount of text it can see at once.

That maximum is the context window.

If the backend sends too much irrelevant context, the model becomes:
- slower
- more expensive
- less focused
- more likely to answer from the wrong context

Crowscap's memory design helps by sending only:
- recent useful conversation turns
- relevant retrieved memories
- source-aware metadata
- explicit missing information

This is why the system should avoid dumping entire documents into chat prompts.

### What Event-Driven Systems Mean

An event-driven system responds to events instead of doing everything immediately in one request.

An event is something that happened.

Examples:
- User uploaded a PDF.
- User saved a YouTube link.
- A reminder became due.
- A memory's review time arrived.
- A push notification failed.

Instead of blocking the user while all work happens, the backend can create a job.

Typical event-driven pattern:

```text
Event happens -> backend records job -> worker processes job -> status updates -> user gets result
```

This is the same broad family of ideas as BullMQ.

### BullMQ, Celery, Queues, And Crowscap's Current Approach

BullMQ is a Node.js job queue built on Redis.

It is commonly used when:
- The backend is Node.js.
- You need background jobs.
- You need retries.
- You need delayed jobs.
- You need scheduled processing.
- You need workers separate from the web server.

Celery is the Python equivalent most people know.

RQ and arq are simpler Python queue options.

Temporal is a heavier workflow engine for complex long-running workflows.

Crowscap currently does not use BullMQ because:
- The backend is Python.
- Pulling in a Node worker just for jobs would add unnecessary runtime complexity.
- The current product stage can use database-backed jobs and FastAPI background tasks.

Current Crowscap job style:

```text
ProcessingJob table + FastAPI BackgroundTasks + notification worker loop
```

The relevant code is:

```text
backend/app/db/models.py
backend/app/services/job_service.py
backend/app/api/v1/jobs.py
backend/app/services/notification_service.py
```

This is not as powerful as BullMQ or Celery, but it is enough for a controlled MVP if the workload is moderate.

When Crowscap grows, the next step should be:

```text
Redis queue + Python worker
```

Good choices:
- RQ for simple Python jobs.
- Celery for mature retries and schedules.
- arq for async Redis jobs.
- Temporal if workflows become complex and need durable step-by-step orchestration.

### What A Processing Job Does

A `ProcessingJob` stores work that should be processed outside the immediate request.

It tracks:
- `job_type`
- `status`
- `step`
- `attempts`
- payload
- result
- error code
- safe error message
- started time
- finished time

This is important because the frontend can ask:

```text
What happened to the URL capture job?
```

The backend can answer:

```text
queued
running
extracting_source
ready
failed
```

That gives the user a mature experience instead of a spinner with no state.

### Why Background Work Matters For Crowscap

Some operations are slow:
- Reading a PDF.
- Fetching a website.
- Fetching YouTube metadata.
- Downloading captions.
- Calling Qwen.
- Generating embeddings.
- Detecting memory relationships.

If all of this happens inside one HTTP request, the user waits too long and the request may timeout.

Better pattern:

```text
Save immediately -> return receipt -> enrich in background
```

For memory products, this is especially important. The user should feel that saving is instant.

### Why SSE Exists Here

SSE means Server-Sent Events.

It is a long-lived HTTP connection from server to browser.

The server can push small updates to the client without the frontend repeatedly asking.

Crowscap uses SSE for live in-app notification updates:

```text
backend/app/api/v1/notifications.py
```

When the client opens the notification stream, the backend can send:
- connected event
- heartbeat
- reminder ready
- recall ready

SSE is useful when:
- Updates are server-to-client only.
- You want simpler infrastructure than WebSockets.
- You do not need bidirectional realtime communication.

WebSockets are better when:
- Both client and server send frequent realtime messages.
- You are building multiplayer, chat presence, collaborative editing, or live dashboards.

Crowscap does not need WebSockets for basic recall events.

### Polling Versus SSE Versus Push Notifications

Polling:

```text
Client asks every N seconds: anything new?
```

Pros:
- Simple.
- Works almost everywhere.

Cons:
- Wastes requests.
- Can be slow or noisy.
- Scales poorly if interval is too aggressive.

SSE:

```text
Client opens a stream. Server sends updates when useful.
```

Pros:
- Good for in-app live updates.
- Less waste than polling.

Cons:
- Only works while app/page is open.
- Needs connection management.

Push notification:

```text
Server sends notification through browser/mobile push infrastructure.
```

Pros:
- Works when app is closed if permissions and platform support are correct.
- Best for bringing users back.

Cons:
- Requires platform setup.
- Delivery is not always instant.
- Android, iOS, PWA, and Expo have different constraints.

Crowscap uses all three ideas in different places, but their jobs are different.

### Why Notification Delivery Has Its Own Table

Notification systems need idempotency.

Idempotency means:

```text
If the same process runs twice, the user should not get duplicate notifications.
```

Without delivery tracking, a worker loop could resend the same recall every minute.

Crowscap stores notification delivery records so the system can know:
- what event was sent
- to which user
- when it was sent
- through which channel
- whether it succeeded or failed

Relevant table:

```text
NotificationDelivery
```

Relevant service:

```text
backend/app/services/notification_service.py
```

### Why Rate Limiting Exists

Rate limiting protects the backend and Qwen credits.

Without rate limiting, a user or bot could spam:
- chat requests
- capture requests
- search requests

This could:
- increase cost
- overload the database
- trigger Qwen rate limits
- degrade the demo experience

Crowscap currently uses an in-memory sliding window limiter:

```text
backend/app/core/rate_limit.py
```

It is good enough for a single Uvicorn worker.

Important limitation:

```text
If the app runs multiple workers, each worker has its own in-memory bucket.
```

At scale, this should move to Redis.

### Why Guardrails Exist

Crowscap stores user knowledge. That makes guardrails more important than in a normal chatbot.

The backend has capture safety checks:

```text
backend/app/services/safety_service.py
```

It checks for:
- credentials
- credit-card-like numbers
- sensitive identifiers
- unsafe capture content

It can mask personal identifiers before saving.

The principle:

```text
The system should protect users from accidentally saving things they should not save.
```

### Why Authentication Has Multiple Paths

Crowscap has web and mobile clients.

The web app and mobile app authenticate differently.

Web path:
- NextAuth handles browser Google login.
- The frontend calls backend through an internal proxy.
- The proxy sends trusted headers.
- Backend validates `X-Crowscap-Proxy-Secret`.

Mobile path:
- Mobile app gets Google ID token or email-code session.
- Backend verifies it.
- Backend issues its own mobile JWT.
- Mobile app sends `Authorization: Bearer <token>`.

Relevant code:

```text
backend/app/core/auth.py
backend/app/api/v1/auth.py
```

Why not use the Google token for everything?

Because the backend should own its session rules. A short app-issued JWT gives the backend a stable user identity across mobile requests.

### Why Email Codes Use Resend

Email login is a passwordless flow.

The user enters email, receives a short code, and verifies it.

Resend is used only to send the email.

The backend still owns:
- code generation
- code hashing
- expiry time
- attempt limits
- session creation

Important security detail:

```text
The code is hashed before storage.
```

That means the database should not store the raw login code.

### Why MCP Exists

MCP means Model Context Protocol.

It lets external AI agents use Crowscap memory tools.

Crowscap exposes tools like:
- search memory
- audit belief
- get due recalls
- get user preferences
- capture text
- submit quick recall
- archive memory

Relevant files:

```text
backend/app/mcp/server.py
backend/app/mcp/tools.py
```

Why this matters:

The user's memory should not only live inside the Crowscap UI. It can become infrastructure that other agents can use.

Example:

```text
An external AI agent can ask Crowscap: "What does this user already know about YC interviews?"
```

Then it can use the memory result to help the user without asking them to repeat context.

Security note:

The current MCP server is intended for trusted/local/demo use. The code comments explicitly say MCP accepts `user_id` from the caller. In a serious multi-tenant deployment, MCP identity should come from authenticated sessions, not a plain caller-provided string.

### Why Source-Aware Memory Matters

Crowscap should not say:

```text
You believe X.
```

when the truth is:

```text
You saved a source that claimed X.
```

That distinction matters.

The backend stores:
- source type
- source title
- source URL
- raw text when available
- confidence
- source strength
- epistemic label

This lets the product answer carefully:

```text
Your saved YouTube source claims...
```

instead of:

```text
You know...
```

### Why Relationship Detection Exists

Memory is more useful when ideas connect.

Relationship detection asks:
- Does this new memory confirm an older memory?
- Does it conflict?
- Does it extend it?
- Does it qualify it?
- Is it unrelated?

Relevant file:

```text
backend/app/services/relationship_service.py
```

This matters because a knowledge system should notice tension.

Example:

```text
Memory A: Cold emails are the best first channel.
Memory B: Founder-led warm intros converted better for this product.
```

Those are not simply two notes. There is a useful tension.

### Why Recall Scoring Exists

Storage is passive.

Recall is active.

The backend decides which memories should resurface by considering signals like:
- due time
- importance
- confidence
- source strength
- user intent
- recent activity overlap
- whether it was already sent
- whether the user archived similar items

Relevant files:

```text
backend/app/services/recall_service.py
backend/app/services/recall_evaluation_service.py
backend/app/services/notification_service.py
```

The goal is not to notify constantly. The goal is to surface the right thing at the right time.

### Why Preferences Exist

Users have different learning styles.

Some want more reminders.
Some want fewer.
Some care about product ideas.
Some care about theology.
Some archive action items often.

Crowscap stores a preference profile:

```text
backend/app/services/preference_service.py
```

Preference learning uses:
- explicit statements
- recurring topics
- source mix
- archived content
- recall reviews

This helps the product adapt without forcing the user to configure everything manually.

### Why Error Handling Is A Product Feature

In an AI memory app, bad errors destroy trust.

Bad:

```text
Unexpected token I in JSON
```

Better:

```text
Crowscap could not reach the database right now. Try again shortly.
```

Better still:

```text
I saved the link, but I could not extract details because the source could not be reached.
```

Crowscap has global exception handling in:

```text
backend/app/main.py
```

Route-level error mapping appears in:

```text
backend/app/api/v1/chat.py
backend/app/api/v1/captures.py
```

The principle:

```text
Backend errors should be safe, honest, and user-understandable.
```

## Section 2: Essential Code-Level Walkthrough

### Backend Folder Map

The backend lives here:

```text
backend/
  app/
    ai/
    api/
    core/
    db/
    mcp/
    schemas/
    services/
    main.py
  alembic/
  scripts/
  tests/
  pyproject.toml
```

Each folder has a different responsibility.

`app/main.py`:
- Creates the FastAPI app.
- Starts and stops app-level background work.
- Registers routers.
- Handles global exceptions.

`app/api/v1/`:
- HTTP endpoints.
- Thin route layer.
- Should not contain most business logic.

`app/services/`:
- Product behavior.
- Capture, extraction, search, recall, notifications, preferences, relationships.

`app/db/`:
- Database models.
- Database session creation.
- Schema bootstrap helpers.

`app/schemas/`:
- Pydantic request and response models.
- API contracts.

`app/ai/`:
- Qwen client.
- Structured output models.

`app/mcp/`:
- MCP server and MCP tool wrappers.

### Application Startup

The app starts in:

```text
backend/app/main.py
```

The key pieces are:

```text
create_app()
lifespan()
app.include_router(api_router, prefix="/api/v1")
```

Startup does this:

1. Load settings.
2. Configure logging.
3. Check the database.
4. Ensure schema exists when possible.
5. Start notification worker if enabled.
6. Register API routes.
7. Register exception handlers.

Shutdown does this:

1. Stop notification worker.
2. Wait briefly for the worker to exit.

The important backend idea is lifecycle management.

Some work must happen once when the app starts, not on every request.

Examples:
- start notification loop
- validate DB
- initialize clients

### Configuration And Environment Variables

Settings are defined in:

```text
backend/app/core/config.py
```

The app uses Pydantic Settings.

This lets the backend read `.env` values like:

```text
DATABASE_URL
QWEN_API_KEY
QWEN_BASE_URL
GOOGLE_CLIENT_ID
RESEND_API_KEY
CROWSCAP_MOBILE_JWT_SECRET
CROWSCAP_WEB_PUSH_VAPID_PRIVATE_KEY
YOUTUBE_API_KEY
```

Why this matters:

Code should not contain secrets.

Bad:

```python
api_key = "real-key-here"
```

Good:

```python
api_key = settings.qwen_api_key_value
```

The settings file also masks database credentials in logs.

That prevents accidental secret leakage.

### Database Connection

Database setup is in:

```text
backend/app/db/session.py
```

Important pieces:

```python
engine = create_engine(...)
SessionLocal = sessionmaker(...)
get_db()
check_database()
```

`get_db()` is a FastAPI dependency.

When a route needs the database, it asks for:

```python
db: Session = Depends(get_db)
```

FastAPI opens a session for the request and closes it after the request finishes.

This pattern prevents leaking database connections.

### Database Models

The main database schema is in:

```text
backend/app/db/models.py
```

The most important tables are below.

#### User

Represents a person using Crowscap.

Stores:
- email
- display name
- image
- provider
- last seen time

Everything important is scoped by user ID.

#### Conversation

Represents a chat thread.

Stores:
- user ID
- title
- created time
- updated time
- optional summary/context metadata

#### ChatMessage

Stores individual user and assistant messages.

This matters for factual conversation questions.

If the user asks:

```text
What was my first message?
```

the backend should query `ChatMessage`, not guess from model memory.

#### Source

Represents original material.

Examples:
- text note
- URL
- YouTube video
- PDF
- reference-only link

Source stores:
- URL
- title
- raw text when available
- metadata
- content hash

#### Capture

Represents the act of saving something.

Source is the material.

Capture is the user action.

That distinction is important.

Example:

```text
Source: YouTube video URL
Capture: User saved it because it will help YC application
```

#### Memory

Represents one atomic idea extracted from a capture.

Stores:
- memory type
- epistemic label
- content
- summary
- confidence
- source strength
- embedding
- review schedule
- status

This is the core unit of Crowscap.

#### ProcessingJob

Represents background work.

Used for URL capture jobs and future long-running processing.

Stores:
- status
- step
- attempts
- payload
- result
- safe error message

#### Reminder

Represents reminder-only nudges.

A reminder is not automatically a memory.

This is important because:

```text
remind me to drink water
```

should not pollute long-term knowledge memory.

#### PushSubscription

Stores browser or mobile push endpoints/tokens.

Used to deliver notifications.

#### NotificationDelivery

Stores notification attempts.

Used to avoid duplicate pushes and debug delivery failures.

#### MemoryRelation

Stores relationships between memory atoms.

Examples:
- confirms
- conflicts
- tension
- extends
- qualifies

#### MemoryArchiveEvent

Records why a memory was archived.

This matters because archiving is a signal.

If the user archives a lot of weak action items, Crowscap can learn to lower priority for similar content.

### API Router Layout

The main API router is:

```text
backend/app/api/v1/router.py
```

It includes:

```text
admin
auth
chat
actions
beliefs
captures
health
jobs
memories
notifications
preferences
qwen
recalls
search
sources
```

This is the public HTTP surface of the backend.

Routes should stay thin.

Good route pattern:

```text
Validate request -> authenticate user -> call service -> map errors -> return response
```

Bad route pattern:

```text
Put all product logic directly inside the route function
```

Crowscap mostly follows the first pattern.

### Authentication Flow

Authentication code is split between:

```text
backend/app/api/v1/auth.py
backend/app/core/auth.py
```

The route file creates sessions.

The core auth file validates sessions on protected requests.

#### Web Auth

The web frontend uses a proxy pattern.

The browser talks to Next.js.

Next.js talks to the backend and includes trusted headers.

The backend checks:

```text
X-Crowscap-Proxy-Secret
```

This prevents random clients from pretending to be the frontend.

#### Mobile Auth

The mobile app sends:

```text
Authorization: Bearer <mobile-jwt>
```

The backend validates that JWT.

That JWT is issued by Crowscap after Google or email login succeeds.

#### Google Login

For mobile Google login:

1. Mobile app gets Google ID token.
2. Mobile app sends token to `/api/v1/auth/mobile-session`.
3. Backend calls Google token verification.
4. Backend checks token audience against configured client IDs.
5. Backend upserts user.
6. Backend returns Crowscap mobile JWT.

Why audience checking matters:

Without it, a token meant for another app could be accepted by Crowscap.

#### Email Code Login

For email login:

1. User enters email.
2. Backend generates code.
3. Backend hashes code.
4. Backend stores hashed code with expiry.
5. Backend sends code using Resend.
6. User submits code.
7. Backend hashes submitted code and compares.
8. Backend issues mobile JWT.

The raw code should not be stored.

### Chat Request Flow

The main chat route is:

```text
backend/app/api/v1/chat.py
```

It calls:

```text
backend/app/services/chat_service.py
```

High-level flow:

```text
POST /api/v1/chat
  -> authenticate user
  -> rate limit
  -> load or create conversation
  -> store user message
  -> inspect recent conversation context
  -> route the message
  -> execute the chosen action
  -> store assistant response
  -> return ChatResponse
```

The chat service is large because it coordinates many behaviors:
- greetings
- identity questions
- memory search
- factual conversation questions
- save previous response
- save pending links
- update recent source context
- reminders
- forgetting/archive requests
- link capture
- PDF capture
- normal conversation

Important lesson:

Chat products are not just "send message to LLM."

A serious chat backend needs routing.

### Chat Routing

Routing decides what the user intends.

Examples:

```text
"what are you" -> identity question
"what did I save about YC" -> memory query
"save that" -> save previous assistant response
"delete that" -> archive recent capture
"remind me tomorrow" -> reminder
"https://..." -> URL capture or reference capture
"what was my first message" -> local conversation fact
```

Crowscap uses a mix of:
- deterministic routing
- Qwen-based routing
- conversation context
- recent pending URL state

This hybrid approach is normal.

Pure hardcoded routing is brittle.

Pure LLM routing can be unstable.

The pragmatic solution is:

```text
Use deterministic rules for safety-critical obvious cases.
Use LLM classification for fuzzy natural language.
Stabilize the route with conversation context.
```

### Why "Save That" Is Harder Than It Looks

When a user says:

```text
save that
```

the backend must decide what "that" means.

Possibilities:
- previous assistant answer
- previous user message
- pending link
- most recent source
- current PDF
- current search result

The code handles this by looking at conversation history and recent capture context.

This is why chat memory products are difficult. Pronouns and short replies require state.

### URL Capture Flow

URL ingestion lives in:

```text
backend/app/services/ingestion_service.py
```

A URL save can follow several paths.

#### Readable Article

Flow:

```text
validate URL
fetch page
extract article text
guard content
extract memories
embed memories
save source/capture/memories
```

#### YouTube Video

Flow:

```text
extract video ID
fetch metadata using YouTube Data API if configured
try oEmbed fallback
try captions with yt-dlp
build metadata/transcript text
extract memory atoms if enough content exists
otherwise save reference metadata honestly
```

The important principle:

```text
If Crowscap cannot read the content, it should not pretend it did.
```

#### Social Or Private Link

Some links are not reliably extractable.

Examples:
- WhatsApp group invites
- private Facebook links
- Instagram links behind login
- pages blocked by bot protection

For these, Crowscap can still save the URL as a reference, especially if the user gives intent.

Example:

```text
will use this for YC application https://...
```

Even if content cannot be read, the memory can preserve:

```text
Saved reference link for: will use this for YC application
```

That is useful later.

### Text Capture Flow

Text capture is in:

```text
backend/app/services/capture_service.py
```

The main function:

```text
create_text_capture()
```

It calls:

```text
create_extracted_text_capture()
```

The flow:

```text
guard content
deduplicate source
extract memory atoms
embed memory atoms
create Source row
create Capture row
create Memory rows
queue perspective notes
detect relationships
commit transaction
build response
```

### Deduplication

Deduplication avoids saving the same source repeatedly.

Crowscap checks:
- user ID
- URL
- content hash

If the same source already exists, it can reuse the existing source and memories instead of creating duplicates.

Why this matters:
- Users paste the same link more than once.
- Retry buttons can resend requests.
- Network failures can cause duplicate submissions.

Backend principle:

```text
Assume clients can retry. Design writes to avoid duplicates where practical.
```

### Extraction Flow

Memory extraction is in:

```text
backend/app/services/extraction_service.py
```

Qwen receives a prompt asking for structured JSON memories.

The extractor expects:
- source title
- inferred intents
- list of memories

Each memory includes:
- type
- epistemic label
- content
- summary
- confidence
- source strength

The service validates Qwen's response.

If validation fails:

```text
repair once -> validate again -> fail safely
```

### Embedding Flow

Embedding is in:

```text
backend/app/services/embedding_service.py
```

It sends memory text to Qwen embedding model.

Then it checks:
- number of embeddings equals number of memories
- no embedding is empty
- dimensions are present

This matters because a mismatch would corrupt search.

If there are five memories, there must be five vectors.

### Search Flow

Search is in:

```text
backend/app/api/v1/search.py
backend/app/services/search_service.py
```

Flow:

```text
POST /api/v1/search
  -> authenticate user
  -> rate limit
  -> embed query
  -> load searchable memories
  -> compute similarity or use vector search
  -> filter archived memories unless requested
  -> return ranked results
```

Search returns metadata like:
- candidate count
- embedded candidate count
- returned count
- top score

That helps debug retrieval quality.

### Recall Flow

Recall is in:

```text
backend/app/api/v1/recalls.py
backend/app/services/recall_service.py
backend/app/services/recall_evaluation_service.py
```

The due recall endpoint:

```text
GET /api/v1/recalls/due
```

loads:
- due memories
- due reminders

Then it ranks memories.

Ranking considers:
- overdue time
- recall score
- importance
- confidence
- source strength
- recent activity overlap
- relationships

The goal is not "show everything due."

The goal is:

```text
Choose the most useful thing to revisit now.
```

### Reminder Flow

Reminder creation is coordinated through chat:

```text
backend/app/services/chat_service.py
backend/app/services/reminder_service.py
```

Reminder examples:

```text
remind me to apply tomorrow at 9am
remind me about this video tomorrow morning
remind me to drink water in one hour
```

Important distinction:

```text
Reminder = a nudge.
Memory = knowledge.
```

Some reminders should not become memories.

### Notification Flow

Notification code is in:

```text
backend/app/api/v1/notifications.py
backend/app/services/notification_service.py
```

There are two notification surfaces.

In-app notification:
- The app is open.
- SSE stream sends updates.

Push notification:
- The app may be closed.
- Web Push or Expo Push delivers the notification.

Notification service does several jobs:
- Select due reminder.
- Select due memory.
- Generate notification copy.
- Avoid duplicates.
- Send web push.
- Send Expo push.
- Record delivery attempts.

### Notification Worker Flow

The notification worker starts during app lifespan if enabled.

Simplified flow:

```text
while app is running:
  open database session
  find users with due reminders or memories
  create notification event
  send push
  record delivery
  sleep configured interval
```

This is an event loop, not a full queue.

It is good for MVP timing.

For scale, move it to a separate worker process.

### MCP Flow

MCP server is in:

```text
backend/app/mcp/server.py
```

Tool logic is in:

```text
backend/app/mcp/tools.py
```

The MCP server wraps backend service functions.

Example:

```text
MCP search_memory
  -> search_memory_tool()
  -> search_memories()
  -> Qwen embeddings
  -> database search
  -> compact result
```

MCP should not duplicate product logic.

It should call the same service layer the API uses.

That keeps behavior consistent.

### Error Handling Flow

There are two levels of error handling.

Route-level:
- Converts known service errors into useful HTTP responses.

Global:
- Catches unexpected exceptions.
- Maps DB/network-like failures to 503.
- Avoids plain-text 500 errors.

Relevant files:

```text
backend/app/main.py
backend/app/api/v1/chat.py
backend/app/api/v1/captures.py
```

Important API principle:

```text
Never make the frontend parse an HTML or plain text crash page as JSON.
```

### Rate Limit Flow

Rate limiting is used in:

```text
backend/app/api/v1/chat.py
backend/app/api/v1/captures.py
backend/app/api/v1/search.py
```

Example:

```python
Depends(rate_limit("chat", limit=30))
```

Meaning:

```text
Allow 30 chat requests per minute per user.
```

In development, rate limiting is bypassed.

That is useful for testing.

### Safety Flow

Capture safety runs before extraction saves content.

Relevant file:

```text
backend/app/services/safety_service.py
```

It can:
- reject highly sensitive content
- mask personal identifiers
- return warnings

The capture response can tell the frontend that redactions happened.

This matters because memory systems can accidentally become stores of sensitive data.

### How The Backend Handles A Save-Link Request

Example user message:

```text
this video will help my YC application https://youtu.be/B5tU2447OK8
```

Expected backend sequence:

1. Chat route receives message.
2. Auth dependency identifies user.
3. Rate limiter checks request.
4. Chat service detects URL and user intent.
5. URL is validated.
6. A reference capture can be created quickly.
7. Metadata and transcript extraction run where possible.
8. If readable content exists, Qwen extracts memory atoms.
9. Embeddings are created.
10. Memories are stored.
11. Assistant response returns a memory receipt.

If extraction fails:

```text
Save reference honestly.
Do not pretend content was read.
Preserve user's intent if provided.
```

### How The Backend Handles "What Is The Link Above About?"

This is a context resolution problem.

The backend should:

1. Look at recent conversation messages.
2. Find the most recent source/link being discussed.
3. Check if extracted memories or metadata exist.
4. Answer from stored source/memory data.
5. If no extracted content exists, say so honestly.

It should not randomly choose an older link.

It should not infer video content if there is no stored evidence.

### How The Backend Handles "Delete That"

This is another context resolution problem.

The backend should:

1. Detect forget/archive intent.
2. Resolve "that" to recent capture or recent memory.
3. Archive or delete the correct records.
4. Confirm clearly.

Relevant functions are in:

```text
backend/app/services/chat_service.py
backend/app/services/memory_lifecycle_service.py
```

Important product principle:

```text
Users should not need memory IDs for obvious recent actions.
```

### How The Backend Handles "What Did I Say First?"

This should be answered from `ChatMessage`.

Correct flow:

```text
load conversation messages
find first user message
return exact content
```

It should not use a general Qwen answer.

Why:

The question asks for a factual conversation record.

If the record exists, retrieve it.

If the record does not exist, say it cannot be found.

Do not guess.

### How The Backend Handles "What Do I Know About Sin?"

This is different from "what did I say first?"

It is a memory query.

Correct flow:

```text
embed query
retrieve relevant memories
include source and confidence
ask Qwen to synthesize from retrieved facts
return answer with caveats
```

The model can synthesize here, but it should stay grounded in retrieved memory records.

### How To Think About Backend Services

Each service should own one kind of business behavior.

Examples:

`capture_service.py`:
- Save text and extracted memories.

`ingestion_service.py`:
- Fetch and parse external content.

`extraction_service.py`:
- Ask Qwen to extract structured memory.

`embedding_service.py`:
- Generate vectors.

`search_service.py`:
- Retrieve memories by meaning.

`recall_service.py`:
- Select memories/reminders due for revisit.

`notification_service.py`:
- Build and send notifications.

`preference_service.py`:
- Maintain user preference profile.

`relationship_service.py`:
- Detect connections between memories.

`memory_lifecycle_service.py`:
- Archive, restore, delete, and list memory lifecycle candidates.

### Backend Interview Concepts From This Project

#### API

An API is the contract between client and server.

Crowscap exposes APIs for chat, capture, search, recall, auth, notifications, and MCP-adjacent behavior.

Interview phrasing:

```text
The frontend is intentionally thin. It calls typed FastAPI endpoints, while the backend owns memory routing, extraction, retrieval, and persistence.
```

#### ORM

An ORM maps Python classes to database tables.

Interview phrasing:

```text
We use SQLAlchemy so product logic can work with typed Python models while still relying on PostgreSQL for durable relational storage.
```

#### Migration

A migration is a controlled database schema change.

Interview phrasing:

```text
Alembic keeps the production schema in step with code changes, so adding a table or column is repeatable across local and deployed environments.
```

#### Transaction

A transaction groups database writes.

Interview phrasing:

```text
Saving a capture touches sources, captures, memories, embeddings, and relationships, so we commit only after the unit of work is consistent.
```

#### Background Job

A job is work that can outlive the immediate HTTP request.

Interview phrasing:

```text
URL ingestion can be slow, so the backend models it as a processing job with status and step tracking. For scale, this can move behind Redis with Celery or RQ.
```

#### Event-Driven System

An event-driven system reacts to something that happened.

Interview phrasing:

```text
When a user saves a link, that event can trigger extraction, embedding, relationship detection, and notification scheduling without making the user wait for every step synchronously.
```

#### Queue

A queue stores jobs until workers process them.

Interview phrasing:

```text
Crowscap currently uses database-backed job records and background tasks. A production-scale version would use a Redis-backed worker queue to improve retries, isolation, and throughput.
```

#### RAG

RAG retrieves stored context before generating an answer.

Interview phrasing:

```text
Crowscap uses RAG over atomic memory records rather than whole documents, which keeps context smaller and makes answers more source-aware.
```

#### Embedding

An embedding is a vector representation of meaning.

Interview phrasing:

```text
We embed each memory atom so users can search by meaning, not only by exact keywords.
```

#### Context Window

The context window is the maximum text the model can see in one call.

Interview phrasing:

```text
The system extracts small memory atoms and retrieves only relevant ones so Qwen gets high-signal context instead of a full dump of user history.
```

#### Idempotency

Idempotency prevents duplicate effects when the same operation repeats.

Interview phrasing:

```text
The backend deduplicates captures by source URL or content hash and tracks notification delivery events so retries do not create duplicate memories or repeated pushes.
```

#### SSE

SSE lets the server push updates over one HTTP stream.

Interview phrasing:

```text
We use SSE for live in-app recall and reminder updates because the data flow is mostly server-to-client and simpler than WebSockets.
```

#### Push Notification

Push brings the user back when the app is not open.

Interview phrasing:

```text
SSE is for live app state. Web Push and Expo Push are for re-engagement when the browser or mobile app is closed.
```

#### Guardrail

A guardrail prevents unsafe or misleading behavior.

Interview phrasing:

```text
The backend validates AI outputs, masks sensitive capture content, refuses to invent unreadable source details, and grounds factual memory questions in database retrieval.
```

### Where To Start Reading The Code

Read in this order:

1. `backend/app/main.py`
2. `backend/app/api/v1/router.py`
3. `backend/app/core/config.py`
4. `backend/app/db/models.py`
5. `backend/app/db/session.py`
6. `backend/app/api/v1/chat.py`
7. `backend/app/services/chat_service.py`
8. `backend/app/services/capture_service.py`
9. `backend/app/services/ingestion_service.py`
10. `backend/app/services/extraction_service.py`
11. `backend/app/services/embedding_service.py`
12. `backend/app/services/search_service.py`
13. `backend/app/services/recall_service.py`
14. `backend/app/services/notification_service.py`
15. `backend/app/mcp/server.py`
16. `backend/app/mcp/tools.py`

This order moves from outer shell to core behavior.

### How To Debug The Backend

Start with the error surface.

If the frontend says "unexpected internal error":
- Check backend logs.
- Find the request path.
- Find exception type.
- Check whether route-level error mapping caught it.

If a save fails:
- Check `chat_service.py` route decision.
- Check ingestion result.
- Check extraction result.
- Check embedding result.
- Check DB commit.

If search is poor:
- Check whether memories have embeddings.
- Check query embedding.
- Check similarity threshold.
- Check archived status.
- Check whether the user's question needs conversation context instead of memory search.

If notifications spam:
- Check due memory selection.
- Check delivery idempotency.
- Check worker interval.
- Check `NotificationDelivery`.
- Check whether recall push throttling is working.

If Google auth fails:
- Check client ID type.
- Check package name.
- Check SHA-1 fingerprint.
- Check backend allowed audiences.
- Check mobile `.env`.
- Rebuild the app if native config changed.

If email auth fails:
- Check `RESEND_API_KEY`.
- Check verified domain.
- Check `RESEND_FROM_EMAIL`.
- Check provider response logs.
- Check whether the backend server was restarted after env change.

### Route-By-Route Backend Map

This section maps the API surface to the backend concept it teaches.

#### `GET /api/v1/health`

File:

```text
backend/app/api/v1/health.py
```

Purpose:
- Confirm the backend process is alive.
- Confirm the database can be reached.
- Confirm whether Qwen is configured.

This is the endpoint to hit first when debugging production.

It does not prove every feature works. It proves the backend can start, load settings, and reach the database.

#### `GET /api/v1/qwen/status`

File:

```text
backend/app/api/v1/qwen.py
```

Purpose:
- Show which Qwen models the backend is configured to use.
- Confirm whether a Qwen API key exists.

This helps separate "the model is broken" from "the backend is missing configuration."

#### `POST /api/v1/qwen/smoke`

Purpose:
- Make one small Qwen call.
- Verify network, API key, model name, and base URL.

This is useful after changing Qwen environment variables.

#### `POST /api/v1/chat`

File:

```text
backend/app/api/v1/chat.py
backend/app/services/chat_service.py
```

Purpose:
- Main conversational entrypoint.
- Routes user messages into capture, search, reminder, forget, identity, factual-conversation, or normal answer flows.

This is the most complex API because natural language is ambiguous.

#### `GET /api/v1/chat/conversation/current`

Purpose:
- Load the active conversation and previous messages.

This is what mobile and web use to restore chat history.

If past messages are not loading, debug this route, user identity, and the conversation query.

#### `POST /api/v1/chat/pdf`

Purpose:
- Receive a PDF upload through chat.
- Extract text with PDF tooling.
- Feed the content into the same memory extraction pipeline.

This endpoint teaches multipart file upload handling.

#### `POST /api/v1/captures/text`

File:

```text
backend/app/api/v1/captures.py
backend/app/services/capture_service.py
```

Purpose:
- Direct text capture outside the chat router.

This is useful for API clients and MCP-like automation.

#### `POST /api/v1/captures/url`

Purpose:
- Direct URL capture outside chat.

This calls the ingestion pipeline directly instead of interpreting the message like chat does.

#### `POST /api/v1/captures/pdf`

Purpose:
- Direct PDF capture outside chat.

This is the non-chat version of PDF ingestion.

#### `POST /api/v1/jobs/captures/url`

File:

```text
backend/app/api/v1/jobs.py
backend/app/services/job_service.py
```

Purpose:
- Create a background URL processing job.
- Return `202 Accepted` plus a job ID.

This route exists to support slow capture workflows.

#### `GET /api/v1/jobs/{job_id}`

Purpose:
- Let the client check a job's status.

This is the polling/status side of the background job pattern.

#### `POST /api/v1/search`

File:

```text
backend/app/api/v1/search.py
backend/app/services/search_service.py
```

Purpose:
- Semantic memory search.
- Embeds the query.
- Compares against stored memory embeddings.
- Returns ranked results.

This teaches RAG retrieval.

#### `GET /api/v1/memories/recent`

File:

```text
backend/app/api/v1/memories.py
```

Purpose:
- Load recently saved active memories.
- Supports pagination with `limit` and `offset`.

This powers the recent memory list on the search page.

#### `GET /api/v1/memories/by-source/{source_id}`

Purpose:
- Return all active memory atoms from one source.
- Include relationships for each memory.

This is useful when the frontend opens a saved source or receipt.

#### `GET /api/v1/memories/{memory_id}`

Purpose:
- Return one memory atom and its relationships.

This powers detail views.

#### `POST /api/v1/memories/{memory_id}/archive`

Purpose:
- Soft-remove a memory from active search and recall.
- Keep an archive event explaining why.

Archiving is reversible and useful as a learning signal.

#### `DELETE /api/v1/memories/{memory_id}`

Purpose:
- Permanently delete a memory.
- Remove or detach related reviews, relationships, reminders, and actions.

This is stronger than archive. It should be used when the user wants the memory gone, not merely hidden.

#### `GET /api/v1/memories/archive-candidates`

Purpose:
- Suggest old or low-value memories that could be archived.

This is part of timely forgetting.

#### `GET /api/v1/memories/compression-candidates`

Purpose:
- Find memory clusters that may be redundant and could later be compressed.

This is an early foundation for memory compaction.

#### `GET /api/v1/memories/perspective-notes/due`

Purpose:
- Show due perspective prompts.

Perspective notes are small nudges that ask the user to revisit assumptions, compare ideas, or strengthen weak evidence.

#### `POST /api/v1/beliefs/audit`

File:

```text
backend/app/api/v1/beliefs.py
backend/app/services/belief_audit_service.py
```

Purpose:
- Search saved memories about a topic.
- Optionally fetch public source leads.
- Ask Qwen to synthesize an audit.

This is not a truth engine. It is a reasoning assistant over saved memory plus source leads.

#### `GET /api/v1/actions`

File:

```text
backend/app/api/v1/actions.py
backend/app/services/action_service.py
```

Purpose:
- List action items created from memories.

Actions are separate from memories because "thing to do" and "thing learned" are different product objects.

#### `GET /api/v1/actions/suggestions`

Purpose:
- Find memories of type `action` that have not yet become action items.

This converts saved learning into execution.

#### `POST /api/v1/actions/from-memory/{memory_id}`

Purpose:
- Create an action item from a memory.
- Avoid duplicate action items for the same memory.

#### `PATCH /api/v1/actions/{action_id}`

Purpose:
- Update action title, description, due date, or status.

#### `GET /api/v1/recalls/due`

File:

```text
backend/app/api/v1/recalls.py
backend/app/services/recall_service.py
```

Purpose:
- Return due memories and reminders.

This is the main recall surface.

#### `POST /api/v1/recalls/{memory_id}/answer`

Purpose:
- Submit a full recall answer.
- Qwen can evaluate whether the user remembered or applied the memory.

#### `POST /api/v1/recalls/{memory_id}/quick`

Purpose:
- Submit a quick recall action like `still_relevant`, `applied`, or `not_now`.

This is a lower-latency path because it does not require a full Qwen evaluation.

#### `POST /api/v1/recalls/reminders/{reminder_id}/complete`

Purpose:
- Mark a reminder done.

#### `POST /api/v1/recalls/reminders/{reminder_id}/snooze`

Purpose:
- Move a reminder forward.

#### `GET /api/v1/sources/{source_id}`

File:

```text
backend/app/api/v1/sources.py
```

Purpose:
- Return original source content for a saved source.

This is how Crowscap preserves source traceability.

#### `GET /api/v1/preferences/me`

File:

```text
backend/app/api/v1/preferences.py
backend/app/services/preference_service.py
```

Purpose:
- Return the user's learned preference profile.

#### `POST /api/v1/preferences/learn-now`

Purpose:
- Force a preference-learning pass.

#### Notification Routes

Files:

```text
backend/app/api/v1/notifications.py
backend/app/services/notification_service.py
```

Routes:

```text
GET /api/v1/notifications/push/public-key
POST /api/v1/notifications/push/subscribe
POST /api/v1/notifications/push/native-token
POST /api/v1/notifications/push/unsubscribe
GET /api/v1/notifications/current
GET /api/v1/notifications/stream
```

Purpose:
- Register browser push subscriptions.
- Register Expo/native push tokens.
- Return current notification state.
- Stream live notification events over SSE.

#### Auth Routes

Files:

```text
backend/app/api/v1/auth.py
backend/app/core/auth.py
```

Routes:

```text
POST /api/v1/auth/mobile-session
POST /api/v1/auth/demo-session
POST /api/v1/auth/email/start
POST /api/v1/auth/email/verify
```

Purpose:
- Convert Google ID tokens into Crowscap mobile sessions.
- Create demo sessions.
- Send email codes.
- Verify email codes.

#### Admin Routes

Files:

```text
backend/app/api/v1/admin.py
backend/app/core/admin_auth.py
```

Routes:

```text
POST /api/v1/admin/login
POST /api/v1/admin/logout
GET /api/v1/admin/stats
GET /api/v1/admin/users
DELETE /api/v1/admin/users/{user_id}
```

Purpose:
- Admin cookie login.
- Basic usage stats.
- User listing.
- Manual full user deletion.

Important warning:

Admin deletion manually deletes related rows because the schema does not rely on strict database-level cascading everywhere. This works, but it means changes to user-owned tables must be reflected in the admin delete function.

### Database Helper Modules

#### `backend/app/db/vector.py`

This module handles pgvector support.

It defines:

```text
QWEN_EMBEDDING_DIMENSIONS = 1024
```

That number must match Qwen `text-embedding-v4`.

It can:
- check whether the current DB bind is Postgres
- format a Python embedding list as pgvector text
- create the `vector` extension
- add `memories.embedding_vector`
- add an HNSW index for cosine search
- backfill a memory's vector column

Important backend concept:

```text
Embedding dimension is schema-critical.
```

If you switch embedding models and the vector size changes, you need a migration and likely re-embedding.

#### `backend/app/db/schema.py`

This module bridges local SQLite development and Postgres production.

For Postgres:
- ensure pgvector schema exists

For SQLite:
- create tables
- patch older local SQLite files with missing columns

This exists because early local development used SQLite, while production needs Postgres/vector support.

#### `backend/app/db/base.py`

This exposes the SQLAlchemy declarative base used by models and migrations.

#### `backend/app/db/migrate_duplicate_users.py`

This is a one-off data repair script.

It handles duplicate users created before auth/user identity rules were fully stable.

One-off migration scripts should be treated carefully:
- run them deliberately
- log what they changed
- avoid keeping them in normal request paths

### Chat Support Modules

#### `backend/app/services/chat_prompts.py`

This file contains prompt builders for chat routing, memory-grounded synthesis, and open conversation.

Why it is separate:
- Prompts are product logic, but they are easier to audit when separated from route orchestration.
- It reduces the size of `chat_service.py`.
- It makes routing prompts easier to regression-test.

Important backend principle:

```text
Prompt text is part of your backend contract when model behavior affects product behavior.
```

#### `backend/app/services/chat_types.py`

This file contains small shared chat data structures.

It keeps route decisions, conversation turns, and typed chat intermediates separate from the large orchestration file.

Why it matters:
- Large chat systems need internal types, not only request/response schemas.
- API schemas describe external contracts.
- Service types describe internal coordination.

### Supporting Memory Services

#### `backend/app/services/perspective_service.py`

This service creates and manages perspective notes.

Perspective notes are not normal memories. They are nudges that ask the user to inspect an idea from another angle.

Examples:
- "This claim may need stronger evidence."
- "This idea may conflict with another saved source."
- "This looks actionable. Should it become a task?"

The service can:
- queue notes for memories
- list due notes
- mark notes accepted
- mark notes dismissed

Why it matters:

```text
Crowscap should not only store what the user learned. It should help the user improve how they think about what they learned.
```

#### `backend/app/services/public_search_service.py`

This service provides public source leads for belief audits.

It has providers for:
- Jina search
- DuckDuckGo HTML fallback
- disabled mode

The belief audit service treats these as leads, not final proof.

This distinction is important. A search snippet is not enough to declare truth. It can only help the user know where to investigate next.

### Alembic Migration Files

Migration files live in:

```text
backend/app/db/migrations/versions/
```

Current migration themes include:

```text
backend/app/db/migrations/versions/0001_initial_postgres_pgvector.py
backend/app/db/migrations/versions/0002_jobs_actions_memory_lifecycle.py
backend/app/db/migrations/versions/0003_reminders.py
backend/app/db/migrations/versions/0004_user_preferences.py
backend/app/db/migrations/versions/0005_users_auth.py
backend/app/db/migrations/versions/0006_pref_perspectives.py
backend/app/db/migrations/versions/0007_recent_memory_index.py
backend/app/db/migrations/versions/0008_notifications.py
backend/app/db/migrations/versions/0009_email_login_codes.py
```

Read migrations when you want to understand how the database evolved.

Read models when you want to understand the current target shape.

### Backend Scripts

Scripts live in:

```text
backend/scripts/
```

#### `run.py`

Starts the backend locally.

Use it for development convenience.

#### `init_db.py`

Initializes local database tables.

Useful for SQLite/local setup.

#### `check_postgres.py`

Checks whether the configured database is Postgres and whether pgvector pieces exist.

It verifies:
- Postgres dialect
- Postgres version
- vector extension
- memories table
- embedding vector column
- HNSW index

Use this after changing `DATABASE_URL`.

#### `backfill_pgvector.py`

Copies existing JSON embeddings into the pgvector column.

Use this when:
- memories already have `embedding_json`
- you later add `embedding_vector`
- you want Postgres vector search to work without re-extracting memories

#### `migrate_sqlite_to_postgres.py`

Moves data from local SQLite into Postgres.

This is useful during migration from early local MVP storage to production-grade relational storage.

#### `qwen_smoke.py`

Makes a small Qwen test call.

Use it to verify API key, model, base URL, and network connectivity.

#### `demo_agent.py`

Runs a demo-oriented script for agent/MCP-style flows.

Use it for presentations and integration sanity checks.

### Test Suite Map

Tests live in:

```text
backend/tests/
```

Each test file maps to a backend risk.

`test_chat.py`:
- chat routing
- save previous response
- link confirmation
- recent source context
- factual conversation behavior
- identity/self-description behavior

`test_captures.py`:
- text, URL, and PDF capture behavior

`test_ingestion.py`:
- URL validation
- article extraction
- YouTube URL handling
- network failure handling

`test_search.py`:
- semantic memory retrieval
- filtering and scoring

`test_recalls.py`:
- due recall selection
- reminder recall behavior

`test_notifications.py`:
- push event creation
- delivery throttling
- notification copy and routing

`test_mobile_auth.py`:
- mobile session creation
- Google token validation behavior
- email-code auth behavior

`test_mcp_tools.py`:
- MCP wrappers call the correct backend services

`test_lifecycle_actions_jobs.py`:
- archive/restore/delete behavior
- action creation
- job status behavior

`test_belief_audit.py`:
- belief audit synthesis and public evidence behavior

`test_public_search.py`:
- Jina/DuckDuckGo parsing and failure modes

`test_qwen_client.py`:
- Qwen error mapping and JSON/embedding behavior

`test_safety.py`:
- capture guardrails and PII masking

`test_relationships.py`:
- relationship detection and filtering

`test_rate_limit.py`:
- in-memory rate limit behavior

`test_error_handling.py`:
- safe JSON error responses

`test_health.py`:
- health endpoint behavior

`test_memories.py`:
- memory detail, recent memory, archive/delete behavior

`test_structured_outputs.py`:
- Pydantic validation of AI structured outputs

Testing principle:

```text
Every fragile user-facing behavior should have a regression test.
```

For Crowscap, the fragile areas are:
- short chat references like "save that"
- link context like "the link above"
- delete/archive recent source
- YouTube failures
- notification throttling
- auth/session identity
- Qwen malformed output

### Backend Coverage Checklist

Use this checklist when studying or changing the backend.

Core app:
- `main.py`
- router registration
- global exception handling
- lifespan worker startup

Configuration:
- `.env`
- `core/config.py`
- secret handling
- model names
- auth secrets
- push settings

Database:
- models
- sessions
- migrations
- pgvector helper
- SQLite compatibility helper

Auth:
- web proxy auth
- mobile JWT
- Google ID token verification
- email code login
- admin cookie auth

Memory pipeline:
- capture
- ingestion
- safety
- extraction
- embedding
- relationship detection
- source preservation

Retrieval:
- semantic search
- recall ranking
- recent memories
- source detail
- memory detail

User control:
- archive
- restore
- delete
- action items
- preferences
- reminders

AI reasoning:
- chat routing
- conversation response
- memory synthesis
- belief audit
- public evidence search
- structured output validation

Async/event behavior:
- background jobs
- processing status
- notification worker
- SSE stream
- web push
- Expo push

Agent access:
- MCP server
- MCP tools
- compact formatters
- trusted demo security assumptions

Operations:
- health check
- Qwen smoke test
- Postgres check
- pgvector backfill
- Alembic upgrade
- systemd/Uvicorn/Nginx deployment

### What Is Strong About This Backend

The backend has several production-minded decisions:

- Typed API contracts.
- Central settings.
- Source-aware memory model.
- AI output validation.
- Atomic memory extraction.
- Embedding-based semantic search.
- User-scoped data.
- Auth separation for web and mobile.
- Rate limiting.
- Safety checks.
- MCP tool surface.
- Push and SSE notification paths.
- Error handling that avoids raw 500 text responses.

### What Is Still MVP-Level

The backend is not finished infrastructure.

Areas that should mature:

- Move long jobs to Redis-backed workers.
- Use Redis-backed rate limiting.
- Strengthen notification scheduling and delivery idempotency.
- Add stronger observability and tracing.
- Add more integration tests for messy chat flows.
- Add queue retries with exponential backoff.
- Make MCP identity authenticated for multi-tenant production.
- Add more formal evaluation datasets for retrieval and recall quality.

This distinction matters.

Good engineering is not pretending the MVP is complete. Good engineering is knowing which parts are solid and which parts need the next layer.

### The Mental Model To Keep

Crowscap is not a chatbot with a database.

It is a memory system with a conversational interface.

That means the backend must care about:
- what happened
- who said it
- why it was saved
- where it came from
- whether it was read
- how confident it is
- when it should return
- whether it still matters
- whether it conflicts with older knowledge
- whether another agent should be able to use it

That is the core backend idea behind the whole project.
