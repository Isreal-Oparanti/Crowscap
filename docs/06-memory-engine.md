# Memory Engine

## Purpose

The memory engine is the core differentiator. It turns saved content into structured, source-aware, queryable, revisable memory.

## Memory Lifecycle

```text
Captured -> Extracted -> Structured -> Embedded -> Related -> Scheduled -> Reviewed -> Consolidated/Archived
```

## Memory Atom Types

The number of atoms is content-dependent. The extractor should split a capture only when it contains distinct ideas, actions, examples, questions, references, or intentions. It should not split merely to create more cards.

For short text captures, the target range is usually 1 to 8 atoms. Longer sources will be chunked later and can produce more atoms across chunks.

Every active memory atom should have an embedding. Embeddings power semantic search, related-memory lookup, tension detection, recall context, and knowledge audits.

Semantic search should work on meaning, not exact words. For example, a query like "how do I get my product to customers" should retrieve memories about distribution or customer acquisition even when those exact words do not appear together.

claim:
A statement that can be supported, challenged, updated, or weakened.

principle:
A reusable rule of thumb or generalizable insight.

definition:
Meaning of a term or concept.

example:
A concrete instance illustrating a claim or principle.

warning:
A risk, failure mode, or "do not do this" insight.

action:
A possible next step, experiment, habit, or implementation detail.

question:
An unresolved question the user should think about or research.

quote:
A memorable phrase worth preserving, used sparingly and with source metadata.

reference:
A source or artifact useful later but not necessarily a learned idea.

intention:
A future learning task such as "watch this later" or "read this later."

## Epistemic Labels

Each memory should carry labels that help avoid false certainty:

- factual_claim
- opinion
- advice
- anecdote
- prediction
- framework
- personal_reflection
- unresolved
- source_summary

## Confidence Model

Confidence is not truth. It is the system's estimate of how strongly this memory is supported inside the user's saved corpus and source metadata.

Inputs:
- Source type: peer-reviewed paper, official documentation, book, personal blog, YouTube opinion, social post, user note.
- Evidence present in source: data, examples, reasoning, citation, anecdote only.
- Number of independent supporting memories.
- Number and strength of challenging memories.
- Freshness or time sensitivity.
- User feedback.

Output:
- low
- medium
- high
- unknown

Always show "why" beside confidence.

## Relation Types

confirms:
An older memory supports or reinforces a new memory.

conflicts:
Two memories cannot reasonably both be true at the same time. Use this sparingly.

tension:
Both memories may be valid, but they pull in different directions depending on context.

extends:
An older memory adds detail, an example, or a next step.

qualifies:
An older memory narrows, limits, or adds conditions to a new memory.

unrelated:
The memories are topically nearby but not meaningfully connected. Do not store these as edges.

Current Phase 0 behavior:
- After a new memory is saved and embedded, Crowscap finds nearby older memories by cosine similarity.
- It excludes memories from the same capture so one source is not mistaken for an independent viewpoint.
- It skips meta memories such as `intention`, `question`, and `reference` for automatic graph edges. They remain saved and searchable.
- It skips those same meta memory types as older relationship candidates.
- It skips very high-similarity near-duplicates because they are usually repeats, not useful tension edges.
- It batches all eligible new memories and their top candidates into one Qwen JSON-mode call per capture.
- It caps total candidate pairs per capture and uses a short timeout because relationship detection is non-critical.
- It starts relationship candidates at `0.50` cosine similarity for the current Qwen embedding model. This is a calibrated default, not a universal vector threshold.
- The classifier must quote exact evidence from both memories. Ungrounded and weak classifications are discarded.
- Memories about different products, actors, mechanisms, or decisions are treated as unrelated even when generic product language makes them topically nearby.
- It stores only meaningful relations in `memory_relations`; `unrelated` results are discarded.
- Relationship detection is non-fatal. If Qwen is temporarily unavailable, capture still succeeds and logs the skipped relationship scan.
- Duplicate captures can backfill a missing relationship scan from older development data. Once a scan completes, the source metadata records that it has been scanned so the same duplicate does not trigger repeated scans.

Future audit signal:
action_gap means the user has saved an idea repeatedly but no linked action or experiment exists. This belongs in recall/audit scoring and is not part of the Phase 0 relationship classifier yet.

## Recall Prompt Types

Phase 0 recall behavior:
- Every saved memory gets a `next_review_at`.
- High-confidence memories are first reviewed after 24 hours.
- Medium-confidence memories are first reviewed after 12 hours.
- Low or unknown confidence memories are first reviewed after 6 hours.
- `GET /api/v1/recalls/due` returns active memories where `next_review_at` is in the past.
- Due memories are ordered by oldest `next_review_at` first, which means most overdue first.
- Due memories include relationship context so review can show connected ideas and tensions.
- Due memories include an adaptive prompt and an epistemic caution where appropriate.
- Recall answers are evaluated against the memory, source metadata, and related memories.
- Evaluations are persisted in `recall_reviews`.
- Evaluation returns an understanding synthesis, missing knowledge, context boundaries,
  and a deeper question rather than only a numeric score.
- Review performance and optional self-rating update `recall_score` and the next interval.

explain:
"Explain this idea in your own words."

defend:
"How would you defend this claim to a skeptic?"

apply:
"What would this change in your current project?"

compare:
"How does this differ from another memory you saved?"

verify:
"What evidence would increase or decrease confidence in this claim?"

contextualize:
"When is this idea true, and when might it fail?"

## Multi-Signal Recall Score

Scheduled recall should not be basic flashcards only.

Use a score like:

```text
priority =
  due_weight
  + importance_weight
  + fragility_weight
  + action_gap_weight
  + topic_recency_weight
  + user_intent_weight
  - fatigue_penalty
  - archive_penalty
```

Signals:
- due_weight: spaced repetition due date.
- importance_weight: many memories relate to it or it appears in audits.
- fragility_weight: memory has tensions, weak evidence, or low confidence.
- action_gap_weight: repeated idea not linked to action.
- topic_recency_weight: user recently captured or searched this topic.
- user_intent_weight: user explicitly marked remember/apply/verify.
- fatigue_penalty: avoid annoying the user with too many prompts.
- archive_penalty: deprioritize stale or dismissed memories.

## Forgetting and Archiving

Do not delete by default. Archive first.

Archive candidates:
- Duplicate memory with stronger canonical version.
- Low-confidence social claim never reviewed and never searched.
- Source failed extraction and user ignored retry.
- Watch-later intention repeatedly snoozed and not relevant.
- Old time-sensitive prediction now expired.
- Memory explicitly marked not useful.

Consolidation:
- Merge repeated memories into a stronger principle when supported by multiple sources.
- Preserve original source links.
- Keep audit trail of merged memory IDs.

## Knowledge Audit

The audit is the main product surface for hackathon differentiation.

Input:
- Topic query.
- Optional user goal or context.

Retrieval:
- Search memory atoms semantically.
- Pull relation edges.
- Pull source metadata.
- Pull recall/action history.

Output:
- Apparent stance.
- Repeated ideas.
- Strongest sources.
- Weakest assumptions.
- Tensions/context dependencies.
- Action gaps.
- Suggested recall/application prompt.
- Memories used as evidence.

Important wording:
- Say "based on what you saved..."
- Say "your current stance appears to be..."
- Do not say "you believe" unless the user explicitly marked it as a belief.
