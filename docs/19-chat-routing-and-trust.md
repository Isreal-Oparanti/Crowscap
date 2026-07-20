# Chat Routing And Trust

Crowscap should not treat every message as a memory operation. The chat layer has three trust boundaries:

1. Normal conversation stays normal.
2. Factual questions about the current chat are answered from stored chat messages, not generated from memory search.
3. External sources are saved only when the user clearly intends to save them.

## Intent Routing

Routing is deliberately hybrid.

Deterministic routing is used only for high-confidence commands and safety-sensitive cases: greetings, acknowledgements, reminders, forget/archive commands, current-chat facts, explicit memory queries, explicit audits, explicit saves, and URL confirmation.

Open-ended natural-language questions are routed by the Qwen classifier. This includes identity and capability questions such as "what are you?", "what is you?", "can you explain yourself?", "what's your purpose?", and "I don't understand this app." These should not depend on a hardcoded list of exact phrases.

When a message is classified as `self`, Crowscap answers from its fixed product knowledge. It must not improvise a generic assistant identity or say it lacks cross-session memory.

## Current-Chat Facts

Questions such as "what was my first message?", "what did I just say?", and "have I thanked you in this chat?" are session facts. They are resolved from the persisted `messages` rows for the active conversation.

The answer should be exact and brief. It should not include memory cards, public evidence, "what is missing", or idea-comparison sections. If the relevant message is not found, Crowscap should say it cannot find it rather than guessing.

Short local follow-ups use the same rule. If the user asks "what question?",
"what made you say that?", or "what is deep?", Crowscap should first inspect the
recent conversation and answer from the actual line being discussed. It should
not search long-term memory unless the user asks about saved knowledge.

## URL Capture Safety

A bare URL in chat is not enough evidence that the user wants permanent memory extraction. Bare URLs now create a confirmation response:

> I found this link. I have not saved it yet. Reply "save this link" if you want Crowscap to read and remember it.

If the user explicitly says "save this", "remember this", "read later", "capture this", or similar around the URL, Crowscap captures it immediately.

This keeps accidental links out of long-term memory while preserving the fast capture flow for intentional saves.

If a message contains substantial user-written content plus a URL, the content
is treated as the primary thing to save. The backend should not collapse a real
note into a link preview just because a URL appears inside it.

Some links are references, not extractable sources. WhatsApp invite links,
Facebook share/reel links, Instagram links, X/Twitter links, and similar
social/app-gated URLs should be kept as references when the user confirms their
importance. Crowscap should not claim it can read private or app-gated content.

Short confirmations are scoped to current state:

- If a pending URL exists, replies like "yeah", "sure", and "go ahead" may confirm it.
- If the user declines with "no thanks" or "ignore it", the pending URL stays unsaved.
- If no pending URL exists, a later "yeah" must remain conversation and must not trigger capture.

## Recent Source Context

After a successful capture, Crowscap may use the just-saved source for short
follow-ups that clearly refer to it, such as "what does this mean?" or "why is
that important?"

It should not inject just-saved source context into ordinary definition or
general conversation questions. For example, after saving a theology video,
"what is thought-provoking?" should be answered as a normal definition question,
not as a forced interpretation of the saved video.

## Why This Exists

The product promise is not just "Crowscap remembers." It is "Crowscap remembers correctly, with user intent." Exact conversation facts require retrieval. Knowledge synthesis requires RAG. Capture requires intent. Mixing those paths creates confident wrongness and memory pollution.
