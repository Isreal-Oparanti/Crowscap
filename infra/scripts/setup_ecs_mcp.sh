#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/crowscap"
BACKEND_ROOT="$APP_ROOT/backend"
MCP_PORT="${CROWSCAP_MCP_PORT:-8010}"
BACKEND_PORT="${CROWSCAP_BACKEND_PORT:-8000}"

cd "$BACKEND_ROOT"

python3 - <<'PY'
from pathlib import Path

env_path = Path(".env")
if not env_path.exists():
    raise SystemExit("Missing /opt/crowscap/backend/.env")

lines = env_path.read_text(encoding="utf-8").splitlines()
cleaned = []
for line in lines:
    if line.startswith("//"):
        cleaned.append("# " + line[2:].lstrip())
    else:
        cleaned.append(line)

if not any(line.startswith("CROWSCAP_MCP_HOST=") for line in cleaned):
    cleaned.extend(
        [
            "",
            "# MCP server",
            "CROWSCAP_MCP_ENABLED=true",
            "CROWSCAP_MCP_HOST=127.0.0.1",
            "CROWSCAP_MCP_PORT=8010",
            "CROWSCAP_MCP_TRANSPORT=sse",
            "CROWSCAP_MCP_SSE_PATH=/mcp/sse",
            "CROWSCAP_MCP_MESSAGE_PATH=/mcp/messages/",
            "CROWSCAP_MCP_STREAMABLE_HTTP_PATH=/mcp",
        ]
    )

env_path.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")
PY

.venv/bin/python - <<'PY'
from app.core.config import get_settings
from app.mcp.server import mcp

settings = get_settings()
print(
    "mcp_import_ok",
    settings.crowscap_mcp_host,
    settings.crowscap_mcp_port,
    settings.crowscap_mcp_sse_path,
)
PY

cat >/etc/systemd/system/crowscap-mcp.service <<UNIT
[Unit]
Description=Crowscap MCP SSE Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BACKEND_ROOT
EnvironmentFile=$BACKEND_ROOT/.env
ExecStart=$BACKEND_ROOT/.venv/bin/python -m app.mcp.server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat >/etc/nginx/sites-available/crowscap <<NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _ api.crowscap.xyz;

    client_max_body_size 25M;

    location /mcp/ {
        proxy_pass http://127.0.0.1:$MCP_PORT;
        proxy_http_version 1.1;

        proxy_set_header Host 127.0.0.1:$MCP_PORT;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";

        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }

    location / {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/crowscap /etc/nginx/sites-enabled/crowscap
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl restart crowscap-backend.service
systemctl enable --now crowscap-mcp.service

nginx -t
systemctl reload nginx

for _ in {1..20}; do
    if curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/v1/health" >/dev/null; then
        break
    fi
    sleep 1
done

echo "== services =="
systemctl --no-pager --full status crowscap-backend.service | sed -n '1,12p'
systemctl --no-pager --full status crowscap-mcp.service | sed -n '1,12p'

echo "== local checks =="
curl -sS "http://127.0.0.1:$BACKEND_PORT/api/v1/health"
echo
timeout 4 curl -sS -N "http://127.0.0.1:$MCP_PORT/mcp/sse" || true
echo

echo "== nginx checks =="
curl -sS "http://127.0.0.1/api/v1/health"
echo
timeout 4 curl -sS -N "http://127.0.0.1/mcp/sse" || true
echo
