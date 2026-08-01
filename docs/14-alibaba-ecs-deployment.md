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

/var/www/crowscap-downloads/
  version.json
  crowscap-latest.apk
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
curl https://api.crowscap.xyz/api/v1/health
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

## Push Notification Worker

SSE keeps the open app updated, but timely reminders need the backend worker to run on ECS. The worker checks due reminders and due recall memories on an interval, sends web/native push through stored subscriptions, and records each sent event so the same reminder or memory does not block the queue.

Required production env values in `/opt/crowscap/backend/.env`:

```bash
CROWSCAP_VAPID_PUBLIC_KEY=...
CROWSCAP_VAPID_PRIVATE_KEY=...
CROWSCAP_VAPID_SUBJECT=mailto:support@crowscap.xyz
CROWSCAP_NOTIFICATION_WORKER_ENABLED=true
CROWSCAP_NOTIFICATION_WORKER_INTERVAL_SECONDS=45
```

After updating the env:

```bash
systemctl restart crowscap-backend
journalctl -u crowscap-backend -f
```

Look for:

```text
notification.worker.start interval=45
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

## Mobile Download Hosting

The Android app is distributed directly while Crowscap is not yet in the Play Store.
The same ECS instance should host the APK and the version manifest:

- `https://api.crowscap.xyz/downloads/version.json`
- `https://api.crowscap.xyz/downloads/crowscap-latest.apk`

Recommended Nginx location block inside the existing `api.crowscap.xyz` server:

```nginx
location /downloads/ {
    alias /var/www/crowscap-downloads/;
    add_header Cache-Control "no-store";
    try_files $uri =404;
}
```

Setup on ECS:

```bash
mkdir -p /var/www/crowscap-downloads
cp /opt/crowscap/deploy/downloads/version.json /var/www/crowscap-downloads/version.json
nginx -t
systemctl reload nginx
curl https://api.crowscap.xyz/downloads/version.json
```

When a new native APK is built:

1. Upload it to `/var/www/crowscap-downloads/crowscap-latest.apk`.
2. Update `/var/www/crowscap-downloads/version.json`.
3. Increase `android.latestVersionCode` so installed apps can detect the new build.
4. Keep `apkUrl` pointed at the latest APK URL.

The mobile app compares its installed Android `versionCode` against this manifest on launch and when returning to the foreground. The update banner appears only when the manifest reports a newer native build.
