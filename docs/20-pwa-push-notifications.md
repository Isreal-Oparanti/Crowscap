# PWA and Push Notifications

Crowscap uses two notification channels because they solve different problems.

```text
SSE  -> live updates while the app is open
Push -> native browser notifications when the app is closed or backgrounded
```

The backend decides when something is due. The browser does not run reminder
timers.

## Runtime Flow

```text
Reminder or recall becomes due
  -> FastAPI creates a lightweight notification event
  -> open browser receives it through SSE
  -> subscribed browser can receive Web Push
  -> notification click opens /recall or /recall/{memory_id}
```

SSE works without extra credentials. Web Push requires VAPID keys.

## Generate VAPID Keys

One common way:

```powershell
npx web-push generate-vapid-keys
```

This prints:

```text
Public Key:
Private Key:
```

The public key may be sent to the browser. The private key must stay on the
backend.

## Backend Environment

Add these on the Alibaba ECS backend:

```text
CROWSCAP_VAPID_PUBLIC_KEY=public_key_from_generator
CROWSCAP_VAPID_PRIVATE_KEY=private_key_from_generator
CROWSCAP_VAPID_SUBJECT=mailto:hello@crowscap.xyz
CROWSCAP_NOTIFICATION_WORKER_ENABLED=true
CROWSCAP_NOTIFICATION_STREAM_INTERVAL_SECONDS=30
CROWSCAP_NOTIFICATION_WORKER_INTERVAL_SECONDS=45
```

Then restart the backend:

```bash
cd /opt/crowscap/backend
systemctl restart crowscap-backend
systemctl status crowscap-backend --no-pager
```

## Frontend Environment

No VAPID secret belongs in Vercel. The frontend only needs the existing backend
proxy variables:

```text
CROWSCAP_BACKEND_URL=https://api.crowscap.xyz
CROWSCAP_PROXY_SECRET=same_secret_as_backend
```

The frontend reads the public push key through:

```text
GET /api/backend/notifications/push/public-key
```

## User Permission

Browsers require notification permission to be requested from a user gesture.
Crowscap therefore shows an explicit `Enable push` control instead of asking
automatically on page load.

If a user blocks notifications in the browser, Crowscap should not keep asking.
They must unblock it from browser site settings.

## Local Testing

Push subscriptions work on:

- `https://` production domains.
- `localhost` during development.

They generally do not work on plain `http://` custom domains.

Checklist:

1. Sign in.
2. Confirm `/manifest.webmanifest` loads.
3. Confirm `/sw.js` loads.
4. Click `Enable push`.
5. Create a reminder due in the next minute.
6. Keep the app open to see SSE.
7. Background the app to test native push.

## Reliability Notes

- Notification deliveries are logged by event key and channel.
- The worker is idempotent, so one due reminder should not create repeated native pushes.
- Expired browser subscriptions are disabled after push providers return 404 or 410.
- If VAPID is missing, Crowscap still keeps SSE live updates working.
