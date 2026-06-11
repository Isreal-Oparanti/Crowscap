# ADR 0002: Memory Language

Status: Accepted.

Date: 2026-06-11.

## Context

The product deals with what users save, remember, question, and apply. It would be tempting to say the system finds "truth." That is risky because saved sources can be wrong, biased, outdated, or context-dependent.

## Decision

Use source-aware language:
- "based on what you saved..."
- "your current stance appears to be..."
- "source strength..."
- "confidence..."
- "tension..."
- "weak assumption..."

Avoid:
- "this is true."
- "you believe this" unless explicitly marked by the user.
- binary contradiction labels unless conflict is direct and clear.

## Consequences

Positive:
- More honest product.
- Stronger trust.
- Better fit for real-world reasoning.
- Easier to defend to judges.

Tradeoffs:
- Output copy must be written carefully.
- The audit feature is more nuanced than a simple answer generator.

