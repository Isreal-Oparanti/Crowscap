# Chat Routing And Trust

Crowscap should not treat every message as a memory operation. The chat layer has three trust boundaries:

1. Normal conversation stays normal.
2. Factual questions about the current chat are answered from stored chat messages, not generated from memory search.
3. External sources preserve the user's intent: readable sources are extracted when possible, and unreadable sources are kept as references without invented content.

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

## Deictic Commands

People naturally say "save that", "keep this", "delete that", or "remove it".
Those words are pointers, not content.

When a short save command points at "that", "this", "it", or the previous
answer, Crowscap should save the previous assistant response rather than the
command text itself. For example, after Crowscap explains how to sell as a
startup founder, "cool save that for me" should save the explanation, not a
memory saying the user wants to save something cool.

When a short forget/delete command points at "that", "this", "it", or the last
saved thing, Crowscap should archive the most recent saved capture in the active
conversation. It should not tell normal users to provide a memory id unless they
are explicitly working at that lower level.

After an archive action, questions such as "what did you just archive?" are
current-chat facts. They should be answered from archive events in the database,
including the actual memory text, not from model inference or generic product
copy.

## URL Capture Safety

Users often drop links quickly because they do not want to lose them. Crowscap
therefore keeps URL messages instead of treating them as accidental noise.
Readable links are extracted when possible. Links that cannot be reliably read
are saved as references, with the user's surrounding words kept as the reason
when available.

If a message contains substantial user-written content plus a URL, the content
is treated as the primary thing to save. The backend should not collapse a real
note into a link preview just because a URL appears inside it.

Some links are references, not extractable sources. WhatsApp invite links,
Facebook share/reel links, Instagram links, X/Twitter links, and similar
social/app-gated URLs should be kept as references immediately. Crowscap should
not claim it can read private or app-gated content.

Readable links should be attempted first. If extraction fails because a source
is private, unavailable, age-restricted, or missing captions, Crowscap should
say that clearly and save the URL as a reference rather than retrying the same
failed extraction path or pretending it knows what is inside.

Short confirmations are scoped to current state:

- If a pending URL exists, replies like "yeah", "sure", and "go ahead" may confirm it.
- If the user declines with "no thanks" or "ignore it", the pending URL stays unsaved.
- If no pending URL exists, a later "yeah" must remain conversation and must not trigger capture.

Short save commands are also scoped to current state. `save this`, `save that`,
and similar messages should save a substantive previous assistant answer. They
must not save greetings, receipts, errors, link prompts, or generic product
copy as memories.

## Recent Source Context

After a successful capture, Crowscap may use the just-saved source for short
follow-ups that clearly refer to it, such as "what does this mean?" or "why is
that important?"

Link-specific follow-ups such as "what is the link above about?" should resolve
to the most recent captured source in the active conversation. If that source was
readable, Crowscap should answer from the memory cards and source snapshot. If it
was only saved as a reference, Crowscap should say exactly what it knows: the URL,
the user's reason for saving it, and any safe metadata such as a video title. It
must not borrow context from older links or nearby memories.

It should not inject just-saved source context into ordinary definition or
general conversation questions. For example, after saving a theology video,
"what is thought-provoking?" should be answered as a normal definition question,
not as a forced interpretation of the saved video.

## Why This Exists

The product promise is not just "Crowscap remembers." It is "Crowscap remembers correctly, with user intent." Exact conversation facts require retrieval. Knowledge synthesis requires RAG. Capture must preserve intent without inventing content. Mixing those paths creates confident wrongness and memory pollution.
