# Autonomous Preferences and Perspective Notes

## Purpose

Track 1 asks for a MemoryAgent that accumulates experience, remembers user preferences, and makes increasingly accurate decisions across multi-turn, cross-session interactions.

For Crowscap, that means two separate learning layers:

1. Preference memory: how the user wants Crowscap to behave.
2. Perspective notes: gentle future prompts that help the user inspect weak or one-sided memories without being judged.

These layers are intentionally separate from semantic memories. A saved idea is not automatically a preference. A perspective note is not automatically truth. The user stays in control.

## Product Rule

Crowscap should help the user notice what they may be missing. It should not act like a truth app that declares final answers.

Use language like:

- "One thing worth considering..."
- "This may depend on context..."
- "You may want stronger evidence for..."
- "If this matters, compare it with..."

Avoid language like:

- "You are wrong."
- "The truth is..."
- "You do not understand..."
- "This proves..."

## Preference Memory

Preference memory stores how the user wants to learn, not what the user learned.

Examples:

- "I prefer concise answers."
- "Challenge my assumptions more."
- "I care mostly about startups and backend engineering."
- "Do not show weak YouTube advice unless there is evidence."
- "Remind me in the evenings."

These update `user_preferences`.

### Preference detection boundaries

A preference is a short command aimed at Crowscap, never a phrase buried inside
pasted content. The extractor enforces two hard boundaries:

1. Length gate: messages longer than 280 characters are never mined for
   explicit preferences. Long messages are content the user wants saved or
   discussed. Without this gate, a pasted essay containing "every day" and
   "please review" was misread as "recall frequency: daily" — and, worse, the
   whole paste was routed as a preference acknowledgment instead of a capture.
2. Sentence scoping: ambient phrases like "every day" or "once a week" only
   count as recall-frequency preferences when the same sentence is actually
   about recall, reminders, or review.

### Preference learning is a background system

Preference learning must never surface in chat except when the entire turn was
the user explicitly telling Crowscap how to behave (an acknowledge turn like
"I prefer short answers"). For every other action — capture, answer,
conversation — learned preferences persist silently and are visible only
through the preferences endpoint (and, later, a settings surface).

Preference learning is also failure-isolated: any exception inside preference
extraction or the autonomous update is logged and swallowed. A preference bug
must never break a chat turn.

### Confidence Tiers

Explicit preferences are high confidence. They come directly from user language and normally get a confidence score around `0.9`.

Behavior-derived preferences are lower confidence. They come from usage patterns such as repeated capture topics, archive behavior, and recall review outcomes. They normally get a confidence score around `0.55` and must be presented as inferred signals.

This distinction matters because the product must not overfit from tiny behavior samples.

## Autonomous Experience Accumulation

Crowscap updates the preference profile from behavior on a throttled schedule. The current implementation is database-only and intentionally cheap:

- Recent active memories infer recurring topics.
- Recent archive events infer memory types or topics to deprioritize.
- Recall reviews infer which memory types seem to retain well.
- Source mix is recorded for transparency.

The autonomous update runs opportunistically after chat messages, but no more than once per 24 hours unless the `/preferences/learn-now` endpoint is called.

This gives the system cross-session adaptation without making every message trigger expensive model calls.

## Perspective Notes

Perspective notes are Crowscap's "ignorance gap" mechanism.

When a memory is saved, Crowscap may queue a future perspective note if the memory is:

- A claim, principle, framework, prediction, or warning.
- Not already strongly supported.
- Based on advice, opinion, prediction, unresolved thinking, weak evidence, or moderate evidence.

Crowscap does not immediately debunk the user. It stores a delayed note linked to the memory.

Example saved memory:

```text
Polling is the best way to handle chat notifications in the backend.
```

Possible future perspective note:

```text
You saved this idea, but Crowscap should not treat it as settled truth yet.
When it resurfaces, compare it against a credible counterexample, boundary condition,
or stronger source before deciding whether to keep, refine, or replace the belief.
Suggested query: Polling is the best way to handle chat notifications in the backend counterarguments evidence limitations
```

The note asks the user to consider nuance. It does not add a new memory automatically.

## User Control

Perspective notes support two decisions:

- Accept: mark the perspective as useful. A future version may convert accepted perspectives into a new memory after user confirmation.
- Dismiss: stop surfacing the note.

This preserves trust. The system can surface a challenge, but the user decides whether it changes their knowledge.

## Current API Surface

Preferences:

- `GET /api/v1/preferences/me`
- `POST /api/v1/preferences/learn-now`

Perspective notes:

- `GET /api/v1/memories/perspective-notes/due`
- `POST /api/v1/memories/perspective-notes/{note_id}/accept`
- `POST /api/v1/memories/perspective-notes/{note_id}/dismiss`

Use `include_future=true` on the due endpoint during development because new notes are scheduled for future surfacing.

## What This Solves For The Hackathon

Autonomously accumulates experience:
Crowscap updates the profile from captures, archives, recall reviews, and chat usage.

Remembers user preferences:
Explicit user preferences and lower-confidence behavioral signals persist across sessions.

Makes increasingly accurate decisions:
Chat, audit, recall, and future surfacing can use the preference profile to adapt tone, evidence strictness, topics, and memory prioritization.

Efficient memory within limited context:
The profile and perspective notes are small structured records. They avoid dumping entire histories into prompts.

Timely forgetting:
Archive signals become behavior data. If the user repeatedly archives certain content types, Crowscap deprioritizes them.

## Next Layer

The current perspective note is a safe queue. The stronger future version should enrich each note with public evidence leads:

1. Generate one focused search query from the memory.
2. Fetch two to three credible public snippets.
3. Store them as source leads, not as truth.
4. Surface the lead during recall or audit.
5. Let the user accept, dismiss, or save the refined idea.

That is the path from passive memory to active, source-aware learning.
