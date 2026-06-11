# ADR 0001: Stack Choice

Status: Accepted.

Date: 2026-06-11.

## Context

The project must be built fast enough for the Qwen Cloud hackathon but mature enough to demonstrate production thinking. The user prefers Next.js + TypeScript for the frontend and FastAPI + Pydantic for the backend.

## Decision

Use:
- Next.js + TypeScript + Tailwind CSS for frontend.
- FastAPI + Pydantic v2 + SQLAlchemy 2.x + Alembic for backend.
- PostgreSQL for relational storage.
- Vector search via pgvector or equivalent vector-capable storage.
- Redis + Celery for background jobs.
- Qwen Cloud through the OpenAI-compatible API.
- Docker for reproducible local development.

## Consequences

Positive:
- Clean separation of UI and backend intelligence.
- Strong typed contracts on both frontend and backend.
- Python backend fits extraction, AI orchestration, and evaluation work.
- Celery keeps slow extraction/model calls outside HTTP request time.

Tradeoffs:
- More moving pieces than a single Next.js full-stack app.
- Celery adds operational complexity.
- Vector support must be verified in the chosen Alibaba Cloud database path.

## Rejected Alternatives

Full-stack Next.js only:
- Faster to scaffold, but weaker for Python extraction and AI worker workflows.

BullMQ:
- Excellent queue, but Node-native. It adds unnecessary runtime mismatch for a Python backend.

Notebook-only prototype:
- Fast for experiments, not enough for production-ready hackathon scoring.

