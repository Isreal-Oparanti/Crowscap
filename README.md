# Crowscap

Source-of-truth documentation for the Qwen Cloud hackathon project.

## Product Promise

Turn what you save into knowledge you can remember, question, and use.

## Product Thesis

Most tools help people store information. Crowscap should help saved information become living, source-aware memory. It should not behave like a passive bookmark folder, a generic note app, or a basic RAG chatbot. It should capture learning fragments, extract atomic memories, track source strength, detect tensions, schedule recall, and expose a belief/knowledge audit that helps the user see what they appear to know, where evidence is weak, and what has not been applied. It should also learn how the user wants to learn: explicit preferences are stored as high-confidence profile settings, while behavior-derived signals from captures, archives, recall reviews, and chat history are stored as lower-confidence adaptation hints.

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
- Database-backed job/status MVP; Redis plus Celery remains optional for scale
- Qwen Cloud via OpenAI-compatible SDK
- Local MCP/SSE server for agent-accessible memory tools

Infrastructure:
- Docker for local reproducibility
- Alibaba Cloud deployment for backend proof
- Object storage for uploaded files and raw extraction artifacts
- Public open-source repository with LICENSE

## Live Surfaces

```text
Frontend: https://crowscap.xyz
API:      https://api.crowscap.xyz/api/v1/health
MCP SSE:  https://api.crowscap.xyz/mcp/sse
```

The MCP SSE endpoint is a long-running stream. A successful quick check returns
an `event: endpoint` line and then keeps the connection open.

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
Capture -> Extract -> Structure -> Relate -> Recall -> Audit -> Adapt -> Improve
```

## Preference Layer

Crowscap keeps preference memory separate from knowledge memory. A normal saved idea becomes a `memory`; an explicit instruction such as "I prefer short answers" or "challenge my assumptions more" updates the durable `user_preferences` profile. The system also accumulates lower-confidence experience signals from behavior, such as recurring topics, archived memory types, and recall review outcomes. That profile is then used by chat, recall, and belief audits without turning casual conversation into memory cards.

## Trust Guardrails

Before content becomes memory, Crowscap now runs deterministic capture guardrails across text, URL/article, YouTube, and PDF ingestion. It rejects obvious secrets, financial account data, private patient-record details, and operational harmful material before extraction or embedding. It masks emails, phone numbers, government ID labels, and home-address labels before storage. Production API routes are rate-limited per authenticated user to protect Qwen credits and reduce abuse.

## Perspective Notes

Crowscap does not immediately debunk saved ideas. When a claim, principle, framework, prediction, or warning is under-evidenced or one-sided, the backend queues a delayed `memory_perspective_note`. Later, Crowscap can surface a gentle prompt such as "one thing worth considering..." and let the user decide whether to accept, dismiss, or save the refined idea.

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
- [Alibaba ECS Backend Deployment](docs/14-alibaba-ecs-deployment.md)
- [MCP Contract](docs/15-mcp-contract.md)
- [ECS MCP Deployment](docs/16-ecs-mcp-deployment.md)
- [Auth and User Isolation](docs/17-auth-and-user-isolation.md)
- [Autonomous Preferences and Perspective Notes](docs/18-autonomous-preferences-and-perspectives.md)

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
