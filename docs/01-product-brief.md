# Product Brief

## Working Name

Crowscap.

The name is a working label. The project should be judged by the product promise and execution, not by the name.

## One-Sentence Promise

Turn what you save into knowledge you can remember, question, and use.

## Core Problem

People consume and save more information than they can integrate. The pain is not only forgetting. The deeper pain is that saved information often never becomes usable knowledge.

## The Five Pain Points

1. Graveyard problem: users save links, videos, screenshots, book excerpts, and notes, then never return.
2. Decay problem: users genuinely understand something, but later remember only the shape of the idea and lose the details.
3. Confidence problem: users cannot easily tell whether a claim is factual, opinion-based, weakly sourced, outdated, or context-dependent.
4. Familiarity without mastery: users hear an idea repeatedly, recognize it, and mistake recognition for understanding or action.
5. Context drift: users learn ideas outside their original context and may later apply them in the wrong situation.

## Target User for the Hackathon Demo

Use one sharp persona in the demo:

An intentional learner, builder, founder, designer, student, or professional who saves learning fragments from many places and needs them to become usable, source-aware memory.

This does not mean the long-term product is only for one niche. It means the demo must be legible fast.

## What Crowscap Is

Crowscap is a memory agent for saved learning fragments. It accepts a source, identifies the user's intent, extracts atomic memory objects, relates them to existing memory, schedules recall, and produces topic audits that expose repeated beliefs, weak evidence, tensions, and unapplied knowledge.

## What Crowscap Is Not

- Not a generic note-taking app.
- Not a read-it-later clone.
- Not a simple bookmark manager.
- Not a basic vector-search wrapper.
- Not a truth oracle.
- Not another recommendation feed.
- Not an Anki clone.

## Product Principles

1. Meet existing behavior: users already save, bookmark, screenshot, highlight, and forward content.
2. Capture intent: "I learned this" is different from "watch later", "verify this", "apply this", "inspiration", or "I disagree."
3. Extract atoms: store structured memory objects, not only raw documents.
4. Preserve source: every memory must point back to its origin.
5. Avoid false certainty: show confidence, evidence strength, and uncertainty.
6. Detect tensions, not just contradictions: intelligent ideas are often context-dependent.
7. Recall when useful: scheduled recall matters, but context-triggered resurfacing is more powerful.
8. Help application: when a saved idea repeats without action, the system should surface that gap.
9. Forget respectfully: archive low-value, duplicate, stale, or ignored memories instead of hoarding forever.

## Capture Intents

Every capture should be classified into one or more intents:

- learned: user believes they learned something from the content.
- remember: user wants recall prompts.
- watch_later: user has not consumed it yet.
- read_later: user has not consumed it yet.
- verify: user wants the claim checked or challenged.
- apply: user wants a next action or experiment.
- reference: user wants it available later.
- inspiration: user wants creative or motivational resurfacing.
- disagree: user is saving something to inspect or challenge.
- question: user is saving an unresolved question.

The UI may ask "Why are you saving this?" but should not require formal tagging. Natural language such as "need to watch this later" should be enough.

## Core Objects

Source:
The original artifact: URL, pasted text, PDF, book excerpt, YouTube transcript, screenshot, or manual note.

Capture:
The user's act of saving a source with optional intent, note, tags, or context.

Memory atom:
A small structured unit extracted from a source. Examples: claim, principle, definition, example, warning, question, action idea.

Relation:
How two memory atoms interact. Examples: supports, challenges, depends_on_context, updates, repeats, illustrates, weakens.

Recall:
A scheduled or context-triggered prompt asking the user to retrieve, explain, apply, or evaluate a memory.

Audit:
A synthesized view of what the user appears to know about a topic, including repeated ideas, source strength, tensions, weak assumptions, and action gaps.

## MVP Promise

The first complete build must support:

- Capture raw text, article/blog URL, YouTube transcript where captions are available, and PDF upload.
- Classify capture intent.
- Extract atomic memories through Qwen Cloud structured output.
- Store memories with source metadata and embeddings.
- Search memories semantically.
- Detect tensions between new and existing memories.
- Generate recall/application prompts.
- Produce a "What do I seem to know about X?" audit.
- Show an evaluation comparison against naive document retrieval.

## Explicitly Out of Scope for Hackathon MVP

- Full WhatsApp production integration.
- Full Instagram/TikTok/LinkedIn/X scraping.
- Browser extension.
- Mobile share sheet.
- Passive ambient browser capture.
- Full social recommendation feed.
- Long-term consumer-grade billing.
- Perfect truth verification across the internet.
- Complex animated knowledge graph as the main product.

