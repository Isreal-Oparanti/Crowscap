# Frontend Architecture

## Stack Decision

Next.js with TypeScript and Tailwind CSS.

Why:
- Next.js gives routing, server/client rendering flexibility, and a clean deployment path.
- TypeScript catches UI contract mistakes early.
- Tailwind supports fast, consistent UI implementation.
- The frontend can stay focused on product experience while the backend owns memory logic.

## Frontend Folder Structure

```text
frontend/
  app/
    layout.tsx
    page.tsx
    capture/
      page.tsx
    inbox/
      page.tsx
    memories/
      page.tsx
      [memoryId]/
        page.tsx
    recall/
      page.tsx
    audit/
      page.tsx
    search/
      page.tsx
    settings/
      page.tsx
    demo/
      page.tsx
  components/
    app-shell/
    capture/
    memory/
    recall/
    audit/
    search/
    ui/
  lib/
    api/
      client.ts
      captures.ts
      memories.ts
      recalls.ts
      audits.ts
      search.ts
    validation/
    formatting/
  hooks/
  styles/
  public/
```

## Interaction Model

Chat is the primary product surface. Every message goes to the backend conversation
router, which decides whether to respond normally, capture a durable learning fragment,
or answer by synthesizing saved memories.

The frontend must never infer this from punctuation or message length. The backend is
the source of truth because acknowledgements and social replies must not become memory.

## Primary Views

Chat:
- Natural conversation is the command center.
- Captures return an inspectable memory receipt.
- Answers lead with synthesis, then show gaps, tensions, next steps, and expandable evidence.
- Ordinary thanks, greetings, and confirmations remain ordinary chat.

Recall:
- Opens from a notification or queue item into a focused conversation.
- Prompts adapt to memory type, evidence quality, and related tensions.
- User answers in natural language.
- System persists the answer, evaluates understanding, exposes missing context,
  reschedules the memory, and asks one deeper question.

Audit:
- Hero feature.
- User asks: "What do I seem to know about X?"
- Shows repeated beliefs, strongest sources, weakest assumptions, tensions, action gaps, and next prompt.

Search:
- Natural language search over saved memories.
- Returns memory atoms first, not raw document chunks first.
- Always includes source links.

Settings:
- Qwen status if useful for local development.
- Capture preferences.
- Recall cadence.
- Data export/delete controls later.

Demo:
- A scripted path for the hackathon video.
- Preloaded sample captures and audit scenarios.

## UI Priorities

1. Make invisible memory work visible.
2. Keep the app work-focused and dense enough for repeated use.
3. Prefer an audit page over an overbuilt node graph.
4. Use memory cards only for repeated items; do not nest cards inside cards.
5. Show labels clearly: claim, principle, example, warning, action, question.
6. Show source strength and confidence without pretending certainty.
7. Use icons for common actions like search, archive, retry, open source, mark applied.
8. Keep text readable and responsive; avoid hero-scale type inside app surfaces.

## Chat Rendering and Receipt Fidelity

Assistant text passes through one safe display renderer before it reaches the
transcript. The renderer supports restrained headings, paragraphs, mixed lists,
quotes, links, inline emphasis, code, and dividers. It performs only display
repairs for common model defects such as concatenated section labels and missing
spacing after sentence punctuation. It never renders model HTML and never
rewrites the meaning of the response.

Typography is intentionally quieter than the former raw dump: assistant prose
uses a 13px regular-weight body with stronger text reserved for headings and
emphasis. Long user pastes remain intact but collapse visually after twelve
lines, with an explicit show-more control. Assistant turns provide a keyboard-
accessible copy action; failures use a distinct error surface with retry kept
next to the error.

Memory receipts are source-aware:

- The summary names the source type, source title, humanized memory count, and
  humanized intents rather than exposing enum values.
- Saved memories and original source are separate accessible tab views.
- Plain text and articles preserve paragraphs; YouTube transcripts receive
  display-only cleanup of timestamps and caption artifacts; reference-only
  sources render labeled title, description, reason, and link fields.
- Stored source content is immutable. All cleanup happens only during rendering,
  so readability improvements never compromise source fidelity or auditability.

## State Management

Server state:
- TanStack Query for API calls, cache, polling job status, and mutations.

Local UI state:
- React state for forms and temporary controls.
- Zustand only if cross-view state becomes painful.

Validation:
- Zod for client-side validation where it improves UX.
- Backend Pydantic remains the source of truth.

## Frontend API Pattern

Frontend should call only backend endpoints.

Never call Qwen Cloud directly from the browser because:
- API keys must stay server-side.
- Backend needs to log, validate, retry, and handle failures.
- The memory pipeline is asynchronous.

## Empty, Loading, and Failure States

Capture:
- Empty: encourage pasting or uploading a learning fragment.
- Loading: show step-level progress when available.
- Failure: show reason category, retry button, and safe fallback such as "paste text manually."

Audit:
- Empty: prompt for a topic.
- Loading: show retrieval, relation review, synthesis stages.
- Failure: explain whether retrieval failed, model output failed validation, or no memories exist.

Recall:
- Empty: show "No due reviews" and optionally a context-triggered prompt.
- Failure: preserve the user's answer and allow retry.

## Accessibility

- Keyboard navigable controls.
- Visible focus states.
- Proper labels for inputs and buttons.
- Color not used as the only signal for confidence or relation type.
- Responsive layout for desktop and mobile widths.
