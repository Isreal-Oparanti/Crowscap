# System Architecture

Crowscap is a source-aware MemoryAgent. The system is designed around one central problem: users do not only need to store information, they need the right piece of knowledge to return at the right moment with enough context to trust it.

## Architecture Goals

- Keep memory persistent across sessions and users.
- Store small, precise memory atoms instead of whole documents in prompt context.
- Preserve original sources so extracted memories can be checked later.
- Use Qwen Cloud for language understanding, structured extraction, embeddings, and synthesis.
- Keep user preferences separate from knowledge memories.
- Treat uncertainty honestly instead of presenting saved notes as final truth.
- Expose stable memory tools through MCP without duplicating backend logic.

## Visual Overview

![Crowscap architecture](../crowscap-architecture-diagram.jpg)

## Implemented Runtime

```text
User
  -> Next.js frontend
  -> Next.js authenticated backend proxy
  -> FastAPI backend on Alibaba Cloud ECS
  -> PostgreSQL memory database
  -> Qwen Cloud for extraction, embeddings, routing, recall, and audit synthesis
```

The browser does not call FastAPI private memory endpoints directly. The Next.js app owns the Google session and forwards signed internal user headers to the backend. FastAPI accepts those headers only when the proxy secret matches.

## Main Components

### Frontend

The frontend is a Next.js application. It owns the product experience:

- Google sign-in and session state.
- Chat-first capture and questioning.
- Memory receipts.
- Semantic search.
- Recall surface.
- Source and memory detail views.
- Preference visibility.

### Backend API

The backend is a FastAPI service deployed on Alibaba Cloud ECS. It owns memory behavior:

- User isolation.
- Chat routing.
- Capture orchestration.
- URL, YouTube, and PDF ingestion.
- Qwen extraction and validation.
- Embedding generation.
- Semantic retrieval.
- Relationship detection.
- Recall scheduling and scoring.
- Belief audits.
- Preference learning.
- Archive and forgetting behavior.

### Qwen Cloud

Qwen Cloud powers the intelligence layer:

- JSON-mode structured memory extraction.
- Natural-language routing when deterministic routing is not enough.
- Embeddings with `text-embedding-v4`.
- Relationship classification between memories.
- Recall answer evaluation.
- Belief audit synthesis.

The main integration file is:

```text
backend/app/ai/qwen_client.py
```

### PostgreSQL

PostgreSQL stores the durable memory system:

- Users.
- Conversations and messages.
- Sources and captures.
- Atomic memories.
- Memory relationships.
- Recall reviews and reminders.
- Preference profiles.
- Actions, jobs, and perspective notes.

Vector support is used so memories can be searched by meaning rather than exact keywords.

### MCP Server

Crowscap exposes read-only MCP tools over SSE:

```text
https://api.crowscap.xyz/mcp/sse
```

Current tools:

- `search_memory`
- `audit_belief`
- `get_due_recalls`
- `get_user_preferences`

The MCP server delegates to existing backend services. It does not reimplement search, audit, recall, or preferences.

## Memory Flow

```text
Capture
  -> input guardrails
  -> extraction with Qwen Cloud
  -> Pydantic schema validation
  -> embedding generation
  -> deduplication
  -> relationship detection
  -> recall scheduling
  -> persistence
```

Original content and extracted memory atoms are stored separately. This lets the user see both the exact thing they saved and Crowscap's structured interpretation.

## Chat Flow

```text
User message
  -> deterministic checks for stateful actions
  -> Qwen-based routing when needed
  -> selected action
  -> database-grounded response
  -> saved conversation turn
```

The router separates:

- Normal conversation.
- Memory questions.
- Capture requests.
- Pending URL confirmation.
- Reminder requests.
- Archive and forgetting requests.
- Crowscap identity and capability questions.
- Factual questions about current conversation history.

Factual questions about stored conversation history are answered from the database rather than guessed from model context.

## Context Window Strategy

Crowscap is built to recall critical memories inside limited context windows.

The backend avoids sending whole documents to Qwen during chat. Instead, it retrieves compact memory atoms and applies context controls:

- Filter by semantic relevance.
- Remove near-duplicate memory context.
- Prioritize by similarity, confidence, source strength, and recency.
- Use recent conversation turns for immediate context.
- Preserve longer-term knowledge through persisted memory rather than unbounded chat history.

This is the key difference from naive RAG. A full article can be thousands of tokens. A memory atom is usually one precise idea.

## Preference Layer

Preference memory is separate from knowledge memory. It stores how the user wants Crowscap to behave, not what the user learned.

Examples:

- Preferred answer style.
- Evidence strictness.
- Communication tone.
- Topics of interest.
- Recall frequency.
- Source preferences.

Explicit preferences are high confidence. Behavior-derived preferences are lower confidence and are treated as adaptation hints, not facts about the user.

## Recall and Forgetting

Recall is not framed as a large queue. The product surfaces one useful memory or reminder at a time.

Forgetting has two forms:

- User-controlled archive: the user can remove memories from active search, recall, audit, and nearby context.
- Deprioritization: low-value or ignored items can become less likely to occupy limited context.

The system does not need to delete every old record to satisfy forgetting. The important behavior is knowing what should stop shaping future answers.

## Current Deployment Shape

```text
Frontend: https://crowscap.xyz
Backend:  https://api.crowscap.xyz
MCP SSE:  https://api.crowscap.xyz/mcp/sse
```

Deployment responsibilities:

- Vercel serves the Next.js frontend.
- Alibaba Cloud ECS runs FastAPI and the MCP server.
- Nginx terminates HTTPS and proxies to local backend processes.
- PostgreSQL stores persistent state.
- Qwen Cloud handles model calls and embeddings.

## Future Hardening

The next production layers are:

- A stronger background processing queue for long ingestion jobs.
- More complete notification delivery.
- Encrypted storage for raw source content.
- Richer perspective notes with public evidence leads.
- MCP write tools after authorization and mutation safety are stronger.
- Broader evaluation against naive RAG.
