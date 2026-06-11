# Crowscap

Source-of-truth documentation for the Qwen Cloud hackathon project.

## Product Promise

Turn what you save into knowledge you can remember, question, and use.

## Product Thesis

Most tools help people store information. Crowscap should help saved information become living, source-aware memory. It should not behave like a passive bookmark folder, a generic note app, or a basic RAG chatbot. It should capture learning fragments, extract atomic memories, track source strength, detect tensions, schedule recall, and expose a belief/knowledge audit that helps the user see what they appear to know, where evidence is weak, and what has not been applied.

## Hackathon Track

Primary track: Track 1 - MemoryAgent.

The project must demonstrate persistent memory, efficient storage and retrieval, timely forgetting or archiving, and recall of critical memories within limited context windows.

## Stack

Frontend:
- Next.js with TypeScript
- Tailwind CSS
- React component architecture
- TanStack Query for server state
- Zod for frontend validation when useful

Backend:
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL with vector search support where available
- Redis plus Celery for background jobs
- Qwen Cloud via OpenAI-compatible SDK

Infrastructure:
- Docker for local reproducibility
- Alibaba Cloud deployment for backend proof
- Object storage for uploaded files and raw extraction artifacts
- Public open-source repository with LICENSE

## Repository Layout

```text
crowscap/
  frontend/               Next.js app, UI, route-level experience
  backend/                FastAPI app, workers, memory engine, MCP server
  infra/                  Docker, deployment, Alibaba Cloud notes
  docs/                   Product, architecture, backend, frontend, roadmap
    adr/                  Architecture decision records
    diagrams/             Mermaid diagrams for submission and planning
```

## Non-Negotiables

- The system must not claim it knows absolute truth.
- The system must represent source strength, confidence, uncertainty, and tension.
- Saved content is not automatically a user belief; phrase audits as "based on what you saved, your stance appears to be..."
- The core loop must work end to end before secondary integrations.
- WhatsApp/Telegram/social integrations are capture channels, not the foundation.
- The demo must show something beyond "save link, search later."

## Core Loop

```text
Capture -> Extract -> Structure -> Relate -> Recall -> Audit -> Improve
```

## Documentation Map

- [Product Brief](docs/01-product-brief.md)
- [Hackathon Strategy](docs/02-hackathon-strategy.md)
- [System Architecture](docs/03-system-architecture.md)
- [Backend Architecture](docs/04-backend-architecture.md)
- [Frontend Architecture](docs/05-frontend-architecture.md)
- [Memory Engine](docs/06-memory-engine.md)
- [Ingestion and Extraction](docs/07-ingestion-and-extraction.md)
- [Data Model](docs/08-data-model.md)
- [API Contract](docs/09-api-contract.md)
- [Security, Cost, and Reliability](docs/10-security-cost-reliability.md)
- [Roadmap and Skills](docs/11-roadmap-and-skills.md)
- [Demo and Evaluation](docs/12-demo-and-evaluation.md)

## Verified Sources

Last verified: 2026-06-11.

- Qwen Cloud hackathon Devpost resources: https://qwencloud-hackathon.devpost.com/resources
- Qwen Cloud hackathon official rules: https://qwencloud-hackathon.devpost.com/rules
- Qwen Cloud first API call: https://docs.qwencloud.com/developer-guides/getting-started/first-api-call
- Qwen Cloud model selection: https://docs.qwencloud.com/developer-guides/getting-started/model-selection
- Qwen Cloud structured output: https://docs.qwencloud.com/developer-guides/text-generation/structured-output
- Qwen Cloud embeddings and reranking: https://docs.qwencloud.com/developer-guides/getting-started/embedding-models
- Qwen Cloud MCP: https://docs.qwencloud.com/developer-guides/text-generation/mcp
- Qwen Cloud cost optimization: https://docs.qwencloud.com/developer-guides/run-and-scale/cost-optimization
- Qwen Cloud safety: https://docs.qwencloud.com/developer-guides/run-and-scale/safety

