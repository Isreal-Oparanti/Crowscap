> **Handoff note for whoever (human or Claude session) opens this next:**
> Everything below was written by a Claude session working through the device
> bridge (file read/write + desktop control only — no terminal/git access),
> diagnosing and fixing a chat/memory retrieval incident. All code changes
> described as "applied"/"committed" below are already present in this
> working tree as **uncommitted** changes — that session could write files
> to disk but never ran `git`. Start with `git status` / `git diff` to see
> exactly what changed, review it, then commit, push, and run
> `alembic upgrade head` (see "Operator instructions" near the bottom —
> there are two pending migrations, 0010 and 0011). This file is also saved
> as a claude.ai Project doc; this copy exists so it ships with the repo
> itself instead of living only there.

---

# Architecture Review: Capture → Extraction → Retrieval → Chat Pipeline

Reviewed directly against the repo at `C:\Users\HP\Desktop\Crowscap` (backend/app). This supersedes the "from gemini" incident doc's root-cause section with verified, line-cited findings — two of its four turn-level diagnoses were wrong about *which* code runs, even though the symptoms were described correctly. There's also a tier of findings the incident doc didn't surface at all: a hard-coded completeness ceiling and a source-identity fan-out bug, both independent of the "13 businesses" incident and both bigger than it.

---

## Part 1 — The four turns, corrected

### Turn 1: misrouted into a "context update" — not an `infer_intent` LLM problem

There is no `infer_intent` function in this codebase. The actual offender is a **deterministic, pre-LLM heuristic** that runs *after* a route has already been chosen and can override it:

`chat_service.py:711` — `_process_recent_reference_context_update()` fires whenever `route.action in {"conversation", "capture", "recent"}` **regardless of what the router (LLM or deterministic) just decided**, and defers entirely to a second heuristic:

`chat_service.py:3139` — `_looks_like_recent_source_context_update()`:
```python
if "?" in message or normalized.startswith(question_starts):
    return False
...
source_markers = ("this video", "that video", ...)
if not any(marker in normalized for marker in source_markers):
    return False
return len(words) >= 5 or len(normalized) >= 35
```
The question-guard only catches a literal `?` or a message that *starts* with a question word. `"so what are the 13 businsess idea in this video"` has no `?` and starts with **"so"**, not "what" — so the guard passes it through. It then matches the `"this video"` source marker and is ≥5 words, so the function returns `True`, and the turn is silently rewritten into "Got it, I added that context to the saved source…", overriding whatever the router actually said.

**This is a correctness bug in one regex-style gate, not a vague LLM over-eagerness problem**, and it's fixable in isolation: check for a question *anywhere* in the message (leading adverbs, "so", "btw", "ok so", etc. are common), not just at position 0.

### Turn 2: confirmed, and the blind spot is intentional by design

`chat_prompts.py:166`, inside `_build_conversation_prompt` (used by `CHAT_CONVERSATION_SYSTEM_PROMPT`):
> "Do not mention saved memories, sources, vector search, recall, or knowledge cards **unless** the recent conversation contains a turn beginning 'Immediate context from the source the user just saved'…"

The plain conversational path is deliberately memory-blind unless a specific marker turn is present in history, and whether that marker gets injected depends on more fragile heuristics (`_should_include_recent_capture_context`, `_has_recent_capture_receipt`). Turn 1's corrupted reply ("I added that context…") doesn't read like a genuine capture receipt, so those detectors likely miss it — **Turn 1's bug destroys the exact signal Turn 2 needed to stay grounded.** Once in plain conversation mode with zero source awareness, Qwen defaults to its generic "I can't watch YouTube videos" refusal. The fix in the incident doc (add a "never say you can't access a saved link" rule) treats the symptom; the actual gap is that this prompt path has no access to source state at all by design.

### Turn 3: not vector search, not a `limit=5`/`limit=10` config value — a hard-coded slice in a hand-templated string function

`chat_service.py:2415`, `_recent_reference_link_reply()`:
```python
memories = result.get("memories")
...
for memory in memories[:5]:            # ← literal, unexplained, uncapped elsewhere
    ...
if reason:
    lines.append(f"You saved it because: {reason}")
```
This function doesn't call `search_memories()` at all. It reads `ProcessingJob.result_json` (see Part 2.2 for why) and slices the first 5 entries of a plain Python list, no ranking, no scoring. `"You saved it because: …"` is `_reference_reason_from_source()` echoing back whatever landed in `Capture.user_intent_text` / the `raw_text` "Why it matters:" line — which, after Turn 1, is the misclassified question text itself. The incident doc's root cause ("tight vector retrieval limits") doesn't apply to this reply path; the real bug is a bare `[:5]` with no justification and no relation to how many cards actually exist.

### Turn 4: confirmed, now fully traceable through three independent narrowing stages

Even on the "real" synthesis path, by the time a question reaches the LLM it has already passed through:
1. **Extraction cap**: never more than 12 memories exist for *any* single capture (Part 2.1).
2. **Retrieval cap**: `chat_service.py:1244` calls `search_memories()` with `limit=6` for the main synthesis path (other call sites use `limit=3` at `:2026` and `limit=8` at `:2820` — none anywhere near 13).
3. **Context-pack cap**: `chat_service.py:2054`, `_pack_memory_context()`, re-ranks the already-trimmed results and drops any that don't fit a **2000-token budget**, with near-duplicate suppression on top.

And the synthesis prompt (`chat_prompts.py:113`) explicitly forbids the model from surfacing any of this: *"Do not mention vector scores or internal retrieval."* So even when evidence is incomplete, the model has no sanctioned way to say "I'm only seeing part of what I saved from this" — it either answers from a partial set or declines. Turn 4's "I don't have the full list" is the model behaving correctly given what it was handed and told.

---

## Part 2 — Findings the incident doc didn't surface

These are independent of the specific "13 businesses" session and will reproduce on *any* source with more than a handful of enumerable items (buyer's guides, "N things" videos/articles, checklists, numbered frameworks — a very common content shape).

### 2.1 — A hard 12-item ceiling, enforced three times, independent of content length

- `ai/structured_outputs.py:184` — `CaptureExtraction.memories: list[ExtractedMemoryAtom] = Field(min_length=1, max_length=12)`. This is a **schema-level** ceiling, not a suggestion.
- `extraction_service.py` sanitizer: `sanitized["memories"] = cleaned_memories[:12]`.
- `capture_service.py`, long-document chunk merge: `if len(merged_memories) >= 12: break`.

On top of the hard ceiling, the extraction system prompt actively biases toward *under*-extraction: *"Return the smallest useful number of memories, usually 1 to 8 for short text."* (`extraction_service.py:232`). A source that explicitly enumerates 13 named items cannot round-trip through this pipeline intact **no matter how retrieval is fixed** — the data is truncated at ingestion, permanently, the moment it's captured. Re-saving the same URL doesn't help either: `_find_existing_source` reuses the existing Source/Memory set rather than re-extracting (see `capture_service.py:109-160`), so an incomplete first extraction is sticky.

This is the real tension behind the doc's "atomic memories vs. holistic synthesis" observation (2A in the original doc) — and it's fixable without abandoning atomic memories: add an explicit **list/ordinal field** on `Memory` (`list_group_id`, `list_position`, `list_total`) and have extraction detect "the source names an explicit N-item list" and either raise the cap for that capture or chunk by list item specifically. Right now there is no schema concept of "this memory is item 7 of 13" anywhere, so the system can't even detect its own incompleteness, let alone fix it.

### 2.2 — Source identity fan-out: two `Source` rows for one real-world link

This is the most consequential structural finding, and it's almost certainly also why Turn 3 reads from a JSON blob instead of a normal query.

- A bare URL save goes through `_create_reference_link_capture()` (`chat_service.py:4949`), creating `Source(source_type="reference")` synchronously with exactly one placeholder `Memory` (`raw_text = "Reference link: {url}"` — this is what the UI's "Original" tab was correctly showing; it isn't a bug, it's working as designed for this path).
- That function then queues a background job (`_create_enriching_reference_link_capture`, `:4873`) which calls `run_url_capture_job()` → `create_url_capture()` → `create_youtube_capture()` → `create_extracted_text_capture()` — **the same full pipeline** used for direct YouTube saves, `source_type="youtube"`.
- `create_extracted_text_capture`'s dedup check, `_find_existing_source()` (`capture_service.py:326`), filters strictly on `Source.source_type == source_type`. `"reference" != "youtube"`, so the dedup **never fires**, and the background job creates a **second, independent `Source`** (own `Capture`, own up-to-12 `Memory` rows) for the same video.

Net effect: one saved link now has two disconnected `Source` records. The conversation's "most recently captured source" pointer resolves to the first (reference) one; the real extracted content lives on an orphaned sibling the conversation has no direct FK to, reachable only via `ProcessingJob.source_id`/`result_json`. That's *why* `_recent_reference_link_reply()` has to dig through a job's cached JSON instead of issuing `SELECT * FROM memories WHERE source_id = ...` — there is no single `source_id` that represents "this video" at that point in the code. The incident doc's proposed fix (deterministic source-scoped lookup) is correct in spirit but incomplete until source identity is unified first: fix the dedup key (match on canonical URL / `resolved_url`, not `source_type`), or merge the reference Source into the enriched Source when the job completes, before source-scoped retrieval can mean anything reliable.

### 2.3 — No source-scoped (or document-scoped) retrieval primitive anywhere in the stack

Confirmed at the schema boundary, not just in chat: `schemas/search.py`'s `SearchRequest` has no `source_id` / `capture_id` field at all. `search_memories()` (`search_service.py`) is pure global top-K cosine similarity — pgvector HNSW when available, falling back to loading up to 1000 rows into Python for manual cosine when it isn't. The FastMCP tool surface exposes the identical limitation to any external MCP client: `mcp/tools.py:46`, `search_memory_tool(limit: int = 5, ...)` — same global-only search, even smaller default. Every "what's in this video" question, even one routed perfectly, competes against the user's *entire* memory corpus for a handful of top-K slots. This needs to exist as a first-class query shape (`search(source_id=...)` or a plain indexed lookup), not be special-cased per chat handler the way `_recent_link_content_reply` currently is.

### 2.4 — Dual embedding storage, synced by convention rather than by the ORM

`Memory.embedding_json` (declared on the SQLAlchemy model) and `memories.embedding_vector` (a pgvector column that **is not declared on the model at all** — it's created and written exclusively through raw `text()` SQL in `db/vector.py`) are two separate representations of the same data. Every memory-creation path has to remember to call `update_memory_embedding_vector()` as a *second* step after setting `embedding_json`; nothing enforces this at the type level, so a new write path that forgets it produces rows that exist but are invisible to pgvector search. `search_memories()` tries pgvector first and falls back silently (`except SQLAlchemyError: ... return None`, logged as a warning only) to the 1000-row Python fallback on *any* pgvector failure, including a dimension mismatch — a correctness/performance cliff with no alerting.

### 2.5 — `chat_service.py`: 5,723 lines, 160 top-level definitions, and genuine dead code

The file contains **byte-for-byte duplicate definitions** of `QwenChatIntentRouter`, `QwenChatSynthesizer`, `QwenChatConversationResponder`, plus duplicated module constants and a duplicated `chat_types` import — lines 128-270 and 223-367 are near-identical (the only diffs: the first `QwenChatSynthesizer.synthesize()` is missing `timeout_seconds`/`max_retries`, and the first import block is missing `ResolvedChatContext`). Python rebinds names at module scope, so **the second block is what actually executes**; the first ~140 lines are dead code sitting at the top of the file, exactly where someone scrolling down to "fix the router" would edit first and silently get no effect. This reads as unresolved merge/rebase damage and should just be deleted.

More importantly, the file implements chat routing as a cascade of roughly **50 regex/keyword heuristic functions** (`_is_forget_command`, `_is_reminder_command`, `_looks_like_self_question`, `_is_substantial_direct_capture`, `_has_explicit_url_capture_intent`, `_is_url_capture_confirmation`, `_looks_like_pending_url_reply`, `_is_save_previous_response_command`, …) layered in front of, and in at least one case (2.1 above) *after and overriding*, the LLM-based router. This isn't a style complaint — it's the structural reason Turn-1-shaped bugs will keep recurring: every new way a user phrases a request is a new potential gap in a hand-maintained regex thicket, several of which are empowered to silently overrule a router that got it right. A single file this size, with this much overlapping heuristic logic, is also close to unreviewable and untestable as a unit — worth splitting along the lines `chat_prompts.py` already demonstrates (it was pulled out specifically "for clarity" and "fully unit-testable in isolation," per its own docstring — the rest of the heuristics deserve the same treatment).

### 2.6 — Structured-output enforcement is client-side only

`ai/qwen_client.py` uses `response_format={"type": "json_object"}` (open JSON mode) rather than a provider-side JSON-schema-constrained mode, so every shape constraint (including the 12-item cap) is discovered only *after* a full generation, via Pydantic validation, then handled through a 3-tier repair cascade (`_validate_or_repair`: sanitize → Python-salvage → LLM re-prompt). The defensive engineering here is solid, but it's compensating for a capability the API likely supports directly, at the cost of an extra round-trip on every malformed response.

---

## Priority to fix, roughly in order of leverage

| # | Fix | Why it's high-leverage |
|---|---|---|
| 1 | Rewrite the question-guard in `_looks_like_recent_source_context_update` to detect a question anywhere in the message, not just a leading word or `?` | One-line-class fix, kills Turn 1 outright, and the same weak-prefix-match pattern likely has siblings worth auditing (`_asks_recent_source_question` has a *better* version of this same check already, at `:2314` — the two should probably share one implementation) |
| 2 | Fix `_find_existing_source` dedup to key off canonical `resolved_url`, not `source_type` equality (or merge-on-complete instead of fan-out) | Removes the two-Source-per-link bug at its root; unblocks real source-scoped retrieval |
| 3 | Add `source_id` (and optionally `capture_id`) to `SearchRequest` / `search_memories`, and a plain non-vector "all memories for this source" path | Replaces both the brittle `[:5]` hand-templated reply and the vector-search-for-everything pattern with one reusable primitive |
| 4 | Raise/condition the 12-item extraction cap on detected list structure; add `list_total`/`list_position` to `Memory` | Makes "did I get all of them" answerable in principle, not just better-hidden |
| 5 | Delete the dead duplicate block in `chat_service.py:128-270`; begin splitting the heuristic layer out of the 5.7k-line file | Prevents the next "I fixed it but nothing changed" cycle |
| 6 | Declare `embedding_vector` on the `Memory` ORM model and assert dimension/sync instead of silently falling back | Removes a silent-failure mode in the primary retrieval path |

---

## Part 3 — Fixes applied (2026-10-09)

All 6 items from the priority table above are implemented and syntax-verified (`python3 -m py_compile` on every touched file — the only verification possible from the device-bridge session; no dependency-manager or test-runner access there). 14 files changed, 1 new migration added.

### Fix 1 — Question-guard false negative (Turn 1)

**Files:** `backend/app/services/chat_service.py`

Added one shared helper, `_is_question_like(normalized: str) -> bool` (line 2136), built on a proper `_QUESTION_WORD_PATTERN` regex rather than a `str.startswith(tuple)` prefix check. Both call sites now share it:
- `_asks_recent_source_question()` (line 2187) — previously had its own separate `question_starts` tuple; now delegates.
- `_looks_like_recent_source_context_update()` (line 3073) — previously only caught a literal `?` or a message *starting* with a question word, which is why `"so what are the 13 businsess idea in this video"` (leading "so") slipped past it into the context-update misroute. Now: `if "?" in message or _is_question_like(normalized): return False`.

### Fix 2 — Source identity fan-out (the two-`Source`-rows bug, Part 2.2)

**Files:** `backend/app/services/chat_service.py`, `backend/app/services/ingestion_service.py`, `backend/app/services/capture_service.py`

1. **`ingestion_service.py:828`** — new `canonical_resolved_url(url: str) -> str`. Normalizes a YouTube URL (short `youtu.be/...`, `watch?v=`, with query params, etc.) to one canonical form via `extract_youtube_video_id`; passes non-YouTube URLs through unchanged.
2. **`chat_service.py:4906`**, `_create_reference_link_capture()` — now stores `resolved_url=canonical_resolved_url(url)` instead of the raw pasted URL. Without this, a naive "match on resolved_url" fix would never have matched a short `youtu.be/...` link against the canonical form the background job stores — exactly the shape from the reported incident.
3. **`capture_service.py:394`**, `_find_existing_source()` — rewritten to match on `resolved_url` **across all source types**, falling back to `source_type` + `content_hash` only when there's no URL to match on.
4. **`capture_service.py:431`**, new `_is_reference_placeholder_source()` — detects a Source that is still just the synchronous reference-only stub.
5. **`capture_service.py:449`**, new `_upgrade_reference_source_with_extraction()` — upgrades a placeholder Source **in place** instead of forking a second Source: archives the placeholder Memory via `MemoryArchiveEvent(reason="superseded")`, updates the Source's fields, creates a new `Capture` under the *same* `source_id`.

**Known gap**: only prevents *new* fan-out going forward. Does not retroactively merge any Source pairs that already split apart in the dev database before this fix.

### Fix 3 — Source-scoped retrieval primitive (Part 2.3)

**Files:** `backend/app/schemas/search.py`, `backend/app/services/search_service.py`, `backend/app/mcp/tools.py`, `backend/app/services/chat_service.py`

Added `source_id: str | None = None` to `SearchRequest`; `search_memories()` branches to a new `_list_memories_for_source()` (plain `Memory` ⋈ `Source` query, no ranking, no hidden cap) when `source_id` is set. `search_memory_tool()` (FastMCP) got the same parameter. `_recent_link_content_reply()` and `_recent_reference_link_reply()` in `chat_service.py` now use this instead of a hardcoded `[:5]` slice — the direct fix for Turn 3.

**Known gap**: the main synthesis path's own search call (`limit=6`) was deliberately not converted to source-scoped retrieval — too risky to touch blind without a test suite.

### Fix 4 — List/ordinal fields + raised extraction cap (Part 2.1)

**Files:** `backend/app/ai/structured_outputs.py`, `backend/app/services/extraction_service.py`, `backend/app/services/capture_service.py`, `backend/app/db/models.py`, `backend/app/db/migrations/versions/0010_memory_list_fields.py`, `backend/app/db/schema.py`

New shared constant `MAX_MEMORIES_PER_EXTRACTION = 40` replaces the bare `12` hardcoded in three places. `ExtractedMemoryAtom` gained `list_group_id`/`list_position`/`list_total`. Extraction prompt now detects an explicitly-enumerated source ("13 Businesses for the Age of AI") and extracts exactly that many items, tagged with a shared list group. `Memory` ORM model + Alembic migration `0010_memory_list_fields` + SQLite self-heal all add the three columns.

### Fix 5 — Dead duplicate code block (Part 2.5)

**Files:** `backend/app/services/chat_service.py`

Deleted the entire first (dead, never-executing) definition block of `QwenChatIntentRouter`/`QwenChatSynthesizer`/`QwenChatConversationResponder` plus duplicated constants/import. File went from 5,723 → 5,579 lines. Pure dead-code removal.

### Fix 6 — `embedding_vector` ORM declaration + fail-loud flag (Part 2.4)

**Files:** `backend/app/db/models.py`, `backend/app/db/vector.py`, `backend/app/services/search_service.py`, `backend/app/core/config.py`, `backend/pyproject.toml`

Added `pgvector>=0.3.6` dependency. `Memory.embedding_vector` now declared on the ORM model, conditionally (only when `pgvector` is importable **and** the configured DB is Postgres — declaring it unconditionally would break every SQLite query once pgvector happened to be installed). New `require_pgvector: bool = False` setting; when `True`, pgvector setup/write/query failures raise `PgVectorUnavailableError` instead of silently falling back.

---

## Incident: `0010_memory_list_fields` migration not applied to production Postgres (2026-10-09, same day as Part 3)

Production Postgres hit `psycopg2.errors.UndefinedColumn: column memories.list_group_id does not exist` on both the chat endpoint and the background notification worker — `alembic upgrade head` was never run after Fix 4 shipped, and the schema self-heal at the time only covered SQLite dev, not Postgres.

**Immediate fix**: ran `alembic upgrade head` manually.

**Structural fix**: `db/schema.py`'s Postgres self-heal was generalized into `_ensure_postgres_additive_columns()`, driven by append-only tables `_POSTGRES_ADDITIVE_COLUMNS`/`_POSTGRES_ADDITIVE_INDEXES` — every additive, nullable, no-backfill column goes here and gets added via `ADD COLUMN IF NOT EXISTS` on every Postgres startup as a safety net. **Alembic remains the system of record**; this only covers the specific class of change that's always safe to apply blind (nothing needing a backfill, `NOT NULL`, or a type change belongs in this table).

---

## Part 4 — Original-tab redesign: organized markdown overview instead of a raw dump (2026-10-09)

**The ask**: the "Original" tab (`GET /sources/{id}` → `SourceContentResponse.original_content`, bound to `Source.raw_text`) should show a well-organized, markdown-formatted write-up of the source, not a raw transcript dump — without changing what extraction/hashing/re-extraction read from.

**Design**: `Source.raw_text` stays completely untouched (extraction, content-hash dedup, re-extraction all still read from it). New field `Source.summary_markdown`, written once by extraction as an organized markdown write-up, generated in the **same** extraction LLM call that produces the atomic memories (no added cost/latency). Every "what should the user see as the original" read site now prefers it, falling back to `raw_text` when no overview exists yet (e.g. a reference-link stub awaiting its background enrichment job).

1. **`ai/structured_outputs.py`** — `CaptureExtraction.source_overview_markdown: str | None`.
2. **`extraction_service.py`** — prompt instructs: organize by topic with markdown headings/bullets, clean up filler/false-starts (video transcripts especially), stay strictly grounded, scale length with real content.
3. **`capture_service.py`** — chunked long-document path joins each chunk's own overview with a markdown horizontal rule rather than making a second LLM call to re-synthesize one; `create_extracted_text_capture()` and `_upgrade_reference_source_with_extraction()` both persist it onto `Source.summary_markdown`.
4. **`db/models.py`**, **`db/migrations/versions/0011_source_summary_markdown.py`**, **`db/schema.py`** — new column, new migration (`down_revision = "0010_memory_list_fields"`), added to both self-heal paths from the start.
5. **`schemas/source.py`**, **`api/v1/sources.py`** — `SourceContentResponse.original_content` now resolves as `source.summary_markdown or source.raw_text` (same field name — no frontend change needed). Added additive `raw_text` field for any consumer that wants the true untouched text.
6. **`capture_service.py`**, `_build_text_capture_response()` — capture-creation response uses the same preference.
7. **`chat_service.py`**, `_recent_link_content_reply()` — the narrow raw-text-snippet fallback (zero active memory cards) now prefers `summary_markdown` too.

**Known gaps**: no backfill for sources captured before this change — they show `raw_text` until re-captured. No second "merge" LLM pass for the chunked case — the section-divided overview is correct but not a single unified rewrite.

---

## Operator instructions — what you need to do after pulling this

1. **Local SQLite dev DB** — no action needed; self-heals automatically on next backend startup.
2. **Postgres / production** — run `alembic upgrade head` to apply **both** `0010_memory_list_fields.py` and `0011_source_summary_markdown.py`. The Postgres self-heal now covers both as a safety net, but Alembic is still the real migration path.
3. **Fix 6's `embedding_vector`** needs `pip install -e .` (or your usual dependency install) to actually activate — it's a no-op, not an error, until then.
4. **`require_pgvector=True`** is opt-in — only set it where Postgres + pgvector is expected to fully work.

## What could not be verified from the device-bridge session

That session had file-level access only (no shell/`device_bash`), so it could not install dependencies, run Alembic, start the backend, or run the test suite against any of these changes — only `python3 -m py_compile` (syntax-level) on every touched file. **Run your real test suite and a smoke-test capture/chat round-trip against a real link before deploying.** The "known gap" items throughout are scope boundaries chosen deliberately, not things missed.
