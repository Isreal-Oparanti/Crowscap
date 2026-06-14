# ADR 0003: Database Development Strategy

Status: Accepted.

Date: 2026-06-11.

## Context

Crowscap needs persistent memory, semantic retrieval, relation detection, recall scheduling, and audit synthesis. The final architecture needs PostgreSQL with vector search support, but early development should not be blocked by cloud database setup.

## Decision

Use SQLite only for Phase 0 local scaffolding and smoke tests.

Use SQLAlchemy models and a `DATABASE_URL` setting from day one so the app can move to PostgreSQL without changing business logic.

Development path:

1. Phase 0:
   - SQLite via `sqlite:///./crowscap_dev.db`.
   - Embeddings stored temporarily as JSON.
   - Small local tests only.

2. Phase 1+:
   - PostgreSQL.
   - pgvector or equivalent vector-capable storage.
   - Proper vector indexes.
   - Migration away from JSON embedding storage.

3. Hackathon deployment:
   - Backend must run on Alibaba Cloud.
   - Prefer Alibaba-hosted PostgreSQL if vector support is confirmed.
   - If managed vector support blocks progress, self-host PostgreSQL + pgvector on Alibaba ECS for the hackathon and document the tradeoff.

## Consequences

Positive:
- Smooth local development starts immediately.
- The app is not tied to SQLite because all database access goes through SQLAlchemy.
- The migration path keeps vector retrieval central to the final architecture.

Tradeoffs:
- SQLite cannot represent the final retrieval performance story.
- JSON embedding storage is temporary and must not become the production design.
- We need an explicit migration before building serious retrieval/evaluation.

