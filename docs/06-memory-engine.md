# Memory Engine

## Purpose

The memory engine is the core differentiator. It turns saved content into structured, source-aware, queryable, revisable memory.

## Memory Lifecycle

```text
Captured -> Extracted -> Structured -> Embedded -> Related -> Scheduled -> Reviewed -> Consolidated/Archived
```

## Memory Atom Types

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

supports:
Memory A strengthens Memory B.

challenges:
Memory A questions or weakens Memory B.

contradicts:
Memory A directly conflicts with Memory B. Use only when conflict is explicit and not merely contextual.

depends_on_context:
Both may be true depending on market, timing, goal, skill level, domain, or assumptions.

updates:
Memory A is newer and revises Memory B.

repeats:
Memory A says substantially the same thing.

illustrates:
Memory A gives an example of Memory B.

action_gap:
The user has saved the idea repeatedly but no linked action or experiment exists.

## Recall Prompt Types

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

