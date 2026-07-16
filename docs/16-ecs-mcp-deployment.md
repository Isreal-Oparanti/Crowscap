# ECS MCP Deployment

This note records the current backend and MCP deployment shape on Alibaba ECS.
It is intentionally operational: enough for a teammate or judge to understand
what is running and how to verify it without reading server history.

## Current Server

- ECS public IP: `47.85.81.243`
- Backend app root: `/opt/crowscap/backend`
- FastAPI service: `crowscap-backend.service`
- MCP service: `crowscap-mcp.service`
- FastAPI local port: `127.0.0.1:8000`
- MCP local port: `127.0.0.1:8010`
- Nginx public port: `80`

The backend and MCP server are separate processes. Nginx proxies normal API
traffic to FastAPI and MCP SSE traffic to the MCP process.

## Runtime URLs

Before DNS and TLS are ready:

```text
http://47.85.81.243/api/v1/health
http://47.85.81.243/mcp/sse
```

After DNS and TLS are ready:

```text
https://api.crowscap.xyz/api/v1/health
https://api.crowscap.xyz/mcp/sse
```

The SSE endpoint stays open by design. A quick `curl` test should show an
`event: endpoint` line, then keep waiting until the command times out.

## Deployed MCP Tools

The first deployed MCP layer is read-only:

- `search_memory`
- `audit_belief`
- `get_due_recalls`
- `get_user_preferences`

Read-only comes first because the public MCP surface should not mutate a user's
memory before auth and deployment hardening are in place.

## Deployment Script

The setup script lives at:

```text
infra/scripts/setup_ecs_mcp.sh
```

It performs these actions on ECS:

1. Cleans invalid `//` comments in `/opt/crowscap/backend/.env`.
2. Adds MCP environment defaults if missing.
3. Verifies `app.mcp.server` imports.
4. Writes `/etc/systemd/system/crowscap-mcp.service`.
5. Updates Nginx to proxy `/mcp/` to `127.0.0.1:8010`.
6. Restarts FastAPI and starts/enables MCP.
7. Runs local backend and MCP smoke checks.

Copy and run it:

```powershell
scp -i "$env:USERPROFILE\Desktop\crowscap.pem" infra/scripts/setup_ecs_mcp.sh root@47.85.81.243:/tmp/setup_ecs_mcp.sh
ssh -i "$env:USERPROFILE\Desktop\crowscap.pem" root@47.85.81.243 "bash /tmp/setup_ecs_mcp.sh"
```

## Server Verification

Run from your local machine:

```powershell
curl.exe -sS http://47.85.81.243/api/v1/health
curl.exe -sS -N --max-time 4 http://47.85.81.243/mcp/sse
```

Run from inside the server:

```bash
systemctl is-active crowscap-backend.service
systemctl is-active crowscap-mcp.service
curl -sS http://127.0.0.1/api/v1/health
timeout 4 curl -sS -N http://127.0.0.1/mcp/sse || true
```

Run a protocol-level MCP tool check inside the server:

```bash
cd /opt/crowscap/backend
.venv/bin/python - <<'PY'
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("http://127.0.0.1:8010/mcp/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([tool.name for tool in tools.tools])

asyncio.run(main())
PY
```

Expected tool list:

```text
['search_memory', 'audit_belief', 'get_due_recalls', 'get_user_preferences']
```

## Alibaba Security Group Check

If local server checks pass but public IP checks fail, the application is
running and the remaining blocker is usually Alibaba ECS networking.

The ECS security group must allow inbound:

```text
TCP 22   from your IP or 0.0.0.0/0 while developing
TCP 80   from 0.0.0.0/0
TCP 443  from 0.0.0.0/0 after TLS is configured
```

Do not expose FastAPI port `8000` or MCP port `8010` directly. They should stay
bound to `127.0.0.1`; only Nginx should face the public internet.

## TLS Later

After `api.crowscap.xyz` resolves to `47.85.81.243`, install TLS with Certbot
or another ACME client. Until DNS resolves, HTTP by public IP is enough to prove
the backend and MCP services are running.
