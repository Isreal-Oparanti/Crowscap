# Alibaba ECS Backend Deployment

This document records the current Crowscap backend deployment path for the Qwen Cloud
hackathon proof of deployment.

## Current Deployment

- Provider: Alibaba Cloud ECS
- Region: US Virginia
- Instance: `ecs.c9i.large`
- OS: Ubuntu 24.04 LTS
- Runtime: FastAPI on Uvicorn, managed by `systemd`
- Reverse proxy: Nginx
- Public backend health URL: `http://47.85.81.243/api/v1/health`
- Future MCP/SSE URL shape: `http://47.85.81.243/mcp/sse`

The MCP/SSE route is not live yet. The backend deployment is ready to host it once the MCP
server is implemented.

## Server Layout

```text
/opt/crowscap/
  backend/
    .env
    .venv/
    app/
    alembic.ini
```

## Services

Backend service:

```bash
systemctl status crowscap-backend
journalctl -u crowscap-backend -f
systemctl restart crowscap-backend
```

Nginx:

```bash
nginx -t
systemctl status nginx
systemctl restart nginx
```

## Health Checks

From the ECS instance:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1/api/v1/health
```

From outside ECS:

```bash
curl http://47.85.81.243/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "app_name": "Crowscap API",
  "environment": "production",
  "database": "ok",
  "qwen_configured": true
}
```

## Deployment Update Flow

```bash
cd /opt/crowscap
git pull
cd backend
.venv/bin/python -m pip install -e .
.venv/bin/alembic upgrade head
systemctl restart crowscap-backend
curl http://127.0.0.1/api/v1/health
```

## Security Notes

- Do not print `.env` values in terminal recordings.
- Startup logs must mask database credentials.
- Keep SSH on port 22 only as needed, and restrict source IP later if possible.
- Keep database access external and encrypted.
- When MCP is added, protect write tools with a bearer token.
