# Auth and User Isolation

Last updated: 2026-07-17

## Why This Exists

Crowscap stores sensitive personal knowledge: saved notes, conversations, source material, recall history, preferences, archived memories, reminders, and belief audits. That means the app cannot behave like a shared demo workspace. Every request that reads or writes memory must be tied to one authenticated user.

## Current Auth Decision

For the hackathon MVP, Crowscap uses Google login through NextAuth in the Next.js frontend.

The browser never calls FastAPI directly for private memory data. Instead:

```text
Browser
  -> Next.js session cookie
  -> Next.js /api/backend proxy
  -> FastAPI with trusted internal user headers
  -> PostgreSQL rows scoped by user_id
```

This keeps the browser from choosing its own `user_id`.

## Trust Boundary

The Next.js proxy forwards identity to FastAPI only after a valid Google session exists.

Forwarded internal headers:

- `X-Crowscap-Proxy-Secret`
- `X-Crowscap-User-Id`
- `X-Crowscap-User-Email`
- `X-Crowscap-User-Name`
- `X-Crowscap-User-Image`

FastAPI accepts these headers only when `X-Crowscap-Proxy-Secret` matches `CROWSCAP_PROXY_SECRET`.

If the secret is missing in production or staging, FastAPI returns a service configuration error rather than silently falling back to a shared user.

## User Scope

The backend now applies the current user to private routes for:

- Conversations and messages
- Captures and sources
- Memories and memory relations
- Search
- Recall and reminders
- Belief audits
- Preferences
- Actions
- Processing jobs

Health checks remain public. Qwen diagnostic endpoints are private because they expose integration state.

## Environment Variables

Frontend:

```text
NEXTAUTH_URL=https://crowscap.xyz
NEXTAUTH_SECRET=<long random secret>
AUTH_GOOGLE_ID=<google oauth client id>
AUTH_GOOGLE_SECRET=<google oauth client secret>
CROWSCAP_BACKEND_URL=https://api.crowscap.xyz
CROWSCAP_PROXY_SECRET=<same secret as backend>
```

Backend:

```text
APP_ENV=production
CROWSCAP_PROXY_SECRET=<same secret as frontend>
CROWSCAP_AUTH_REQUIRED=true
```

Local development can still run without auth headers when `APP_ENV=development`, but production must use `APP_ENV=production` and the proxy secret. If the backend is deployed with `APP_ENV=development` and no `CROWSCAP_PROXY_SECRET`, every proxied request can fall back to the shared `dev_local_user`, which makes different Google users appear to share one memory workspace.

## Google OAuth Setup

Create an OAuth web client in Google Cloud and add these redirect URIs:

```text
http://localhost:3000/api/auth/callback/google
https://crowscap.xyz/api/auth/callback/google
https://www.crowscap.xyz/api/auth/callback/google
```

Use the Google client ID and client secret in the frontend environment.

## Legacy Data Note

Earlier development data was saved before real user isolation. Those rows may have `user_id = NULL` or the old local development user. After signing in, the app will show only rows belonging to the current Google user. For a demo account, migrate or re-capture the desired demo memories under that signed-in user.

## Future Hardening

- Add CSRF and rate-limit protection around mutation routes.
- Add account deletion and full data export.
- Add encrypted storage for raw source content.
- Move from proxy headers to signed short-lived internal tokens if the backend is exposed to multiple internal clients.
- Add organization/workspace membership only after single-user privacy is stable.
