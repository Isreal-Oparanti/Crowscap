# Crowscap Frontend

Chat-first Next.js interface for the Crowscap memory agent.

## Run locally

```powershell
npm install
npm run dev
```

The frontend proxies API calls to `http://127.0.0.1:8000` by default. Override it with:

```env
CROWSCAP_BACKEND_URL=http://127.0.0.1:8000
```

Open `http://127.0.0.1:3000`.

Capture receipts separate two views:

- `Memories` shows Crowscap's structured, searchable interpretation.
- `Original` shows the user's exact submitted text without rewriting it.

The recall workspace also loads the original source on demand, so active retrieval never removes access to the source-of-record.

The Next.js "Slow filesystem detected" message is a development performance warning,
not an application error. The first route compilation can be slow on Windows because
`.next/dev` contains many small generated files. Later requests are normally much
faster. A `503` from `/api/backend/...` means the FastAPI backend on port `8000` is not
available.
