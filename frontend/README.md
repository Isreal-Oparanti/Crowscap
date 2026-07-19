# Crowscap Frontend

Next.js interface for Crowscap's conversational memory experience.

The frontend is intentionally chat-first. Users should not need to understand memory databases, embeddings, or retrieval pipelines. They should be able to paste what they found, ask what they know, revisit something important, or tell Crowscap how they prefer to learn.

## Product Surfaces

- Chat: capture, ask, save, search, set reminders, and audit beliefs from natural language.
- Recall: one useful memory or reminder at a time, not a large task queue.
- Search: semantic memory search over saved ideas.
- Source views: show original saved content beside extracted memory atoms.
- Preference surfaces: show what Crowscap has learned about how the user wants to learn.
- Auth boundary: Google sign-in before private memory can be accessed.

## Stack

- Next.js
- TypeScript
- Tailwind CSS
- TanStack Query
- NextAuth

## Local Setup

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

The frontend proxies backend calls through Next.js API routes. By default, local development expects the backend at:

```text
http://127.0.0.1:8000
```

Override it with:

```env
CROWSCAP_BACKEND_URL=http://127.0.0.1:8000
```

## Authentication Environment

Local and production authentication use Google OAuth through NextAuth.

Required variables:

```env
NEXTAUTH_URL=http://127.0.0.1:3000
NEXTAUTH_SECRET=replace_with_long_random_secret
AUTH_GOOGLE_ID=google_oauth_client_id
AUTH_GOOGLE_SECRET=google_oauth_client_secret
CROWSCAP_BACKEND_URL=http://127.0.0.1:8000
CROWSCAP_PROXY_SECRET=same_secret_as_backend
```

Production values use:

```env
NEXTAUTH_URL=https://crowscap.xyz
CROWSCAP_BACKEND_URL=https://api.crowscap.xyz
```

The frontend signs backend proxy requests with `CROWSCAP_PROXY_SECRET`, and the backend scopes each request to the authenticated user.

## User Experience Principles

Crowscap should feel like a private learning workspace, not a generic chatbot.

The interface should:

- Let normal conversation remain normal.
- Ask for confirmation before saving accidental links.
- Show memory receipts after successful captures.
- Keep original source text accessible.
- Surface one useful recall instead of overwhelming the user with a backlog.
- Use plain language for memory relationships and evidence quality.
- Avoid turning every response into a lecture or audit.
- Make privacy and user boundaries visible.

## Important Flows To Test

1. Sign in with Google.
2. Paste a useful paragraph and confirm memory cards appear.
3. Paste a bare link and confirm Crowscap asks before saving it.
4. Reply naturally, such as `yeah` or `yes please`, and confirm the pending link is processed.
5. Ask a normal conversational question and confirm unrelated memories do not appear.
6. Search for a saved idea by meaning, not exact wording.
7. Open recall and confirm it shows one focused nudge.
8. Archive a memory and confirm it stops surfacing.

## Backend Dependency

If the frontend shows a backend error, first check:

```text
https://api.crowscap.xyz/api/v1/health
```

For local development:

```text
http://127.0.0.1:8000/api/v1/health
```

A `503` from `/api/backend/...` usually means the FastAPI backend is not available or the configured backend URL is wrong.

## Build

```powershell
npm run build
```

The Next.js development warning `Slow filesystem detected` is a local Windows performance warning. It is not an application error.

## Related Docs

- `../docs/05-frontend-architecture.md`
- `../docs/09-api-contract.md`
- `../docs/17-auth-and-user-isolation.md`
- `../docs/19-chat-routing-and-trust.md`
