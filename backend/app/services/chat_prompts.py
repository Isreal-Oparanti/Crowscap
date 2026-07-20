"""Chat prompt templates and builder functions for Crowscap.

Extracted from chat_service.py.  All functions here are pure (no DB, no AI
calls) and depend only on schema types — fully unit-testable in isolation.

The builder functions accept pending_url as an explicit argument so there is
no hidden dependency on chat_service internals.
"""
from __future__ import annotations

from app.schemas.chat import ConversationTurn
from app.schemas.search import SearchResponse


def _build_router_prompt(*, message: str, history: list[ConversationTurn], pending_url: str | None = None) -> str:
    history_text = "\n".join(
        f"{turn.role}: {turn.content}" for turn in history[-6:]
    ) or "No earlier turns."
    pending_state = (
        f"pending_url: {pending_url}"
        if pending_url is not None
        else "No pending app action."
    )
    return f"""Classify the user's latest message.

Return JSON:
{{
  "action": "acknowledge" | "conversation" | "capture" | "answer" | "audit" | "forget" | "reminder" | "self",
  "reply": "short natural reply only when action is acknowledge, otherwise null",
  "reason": "brief classification reason"
}}

Definitions:
- acknowledge: greetings, thanks, agreement, confirmation, social replies, or conversational continuation with no durable knowledge to save.
- conversation: the user asks a normal question, asks for advice, opens a topic, asks about this current chat/session, or wants normal assistant continuity without explicitly needing saved memories.
- capture: the user supplies a substantive learning fragment, claim, source, note, reflection, or explicitly asks to remember/save something.
- answer: the user explicitly asks about saved/learned knowledge, asks what they know from memory, asks to search memories/notes, requests comparison across saved memories, or wants help thinking with their knowledge base.
- audit: the user explicitly asks Crowscap to challenge, audit, evidence-check, or compare a belief against public evidence.
- forget: the user asks to forget, archive, stop showing, stop reminding, remove, or delete a memory or topic from active memory.
- reminder: the user asks to remind them at a specific later time, with or without saving the content as memory.
- self: the user asks what Crowscap is, what it does, how it works, who built it, what its purpose is, whether it is just a chatbot, or what its current limitations are.

Never classify thanks, "okay", "this makes sense", or simple agreement as capture.
Never run saved-memory search for questions about only the current chat, such as "have I thanked you before in this chat?" or "what was the first thing I said?"
Do not classify ordinary advice questions as answer just because they are questions.
Do not classify ordinary memory questions as audit unless the user explicitly asks for an audit, challenge, evidence check, reliability check, or public evidence comparison.
Do classify "forget what I know about X" as forget, not audit.
Do classify "remind me in 1 hour" as reminder, not capture.
Do classify identity/capability questions as self regardless of exact phrasing, typos, informal language, or indirect wording. Examples: "what are you?", "what is you?", "can you explain yourself?", "what's your purpose?", "I don't understand this app", "what can you do?", "how does Crowscap work?"
Do not treat a bare URL as intentional long-term memory unless the surrounding words clearly ask to save, remember, read, or capture it.
Do not save every user message. Capture only when there is durable informational content or explicit saving intent.

Pending app state:
{pending_state}

Pending action rules:
- If pending_url exists and the latest message semantically confirms saving, reading, processing, or handling that link, classify as capture even if the user says it informally, with typos, or indirectly.
- If pending_url exists and the latest message declines, cancels, ignores, or moves away from that link, classify as conversation and use reply to say the link will stay unsaved.
- If no pending_url exists, do not classify short confirmations such as "yes please", "sure", "go ahead", or "okay" as capture.
- If the latest message contains a new substantive note, question, or topic, classify the new message on its own instead of forcing it to act on a pending link.

Recent conversation:
{history_text}

Latest user message:
{message}
"""


def _build_synthesis_prompt(
    *,
    question: str,
    history: list[ConversationTurn],
    search: SearchResponse,
    relation_context: list[str],
    preference_context: str,
) -> str:
    history_text = "\n".join(
        f"{turn.role}: {turn.content}" for turn in history[-6:]
    ) or "No earlier turns."
    evidence_text = "\n".join(
        (
            f"[{index}] {result.content}\n"
            f"Source: {result.source_title or 'Untitled source'}; "
            f"type={result.memory_type}; epistemic_label={result.epistemic_label}; "
            f"confidence={result.confidence}; source_strength={result.source_strength}; "
            f"similarity={result.similarity_score}"
        )
        for index, result in enumerate(search.results, start=1)
    ) or "No relevant personal memories were found."
    relations_text = "\n".join(relation_context) or "No stored relationships were found."

    return f"""Answer the user's question as their source-aware second brain.

Return JSON:
{{
  "answer": "a natural, direct answer in 1-4 short paragraphs",
  "knowledge_gaps": ["important missing evidence, context, or understanding"],
  "tensions": ["plain-language description of ideas that disagree or depend on context"],
  "next_step": "one useful question or action, or null"
}}

Rules:
- Synthesize; do not dump or merely list memory cards.
- Make the product's value clear by connecting repeated ideas and explaining what they mean together.
- Treat saved memories as the user's information history, not automatically as objective truth.
- Explicitly notice opinions, advice, weak sources, unsupported claims, and missing evidence.
- If memories disagree, explain the difference and when context changes which idea applies.
- Use plain language for user-facing text. Do not use the word "tension".
- knowledge_gaps should name what the user would need to understand or verify before treating the conclusion as reliable.
- You may use general reasoning to explain a gap, but do not pretend it came from the user's saved sources.
- If no personal memories were found, answer helpfully but clearly say this answer is not grounded in their saved memory yet.
- Use only the memories that directly answer this question. Ignore unrelated memories even if they appear in the retrieval list.
- Do not add "what is still missing", "ideas worth comparing", or a next-step coaching section for simple factual or definition-style questions.
- If the user's question is really about the immediate chat, answer the immediate chat fact directly and do not reinterpret their wording as meaningful.
- Do not mention vector scores or internal retrieval.
- Follow the learned user preferences when they do not conflict with safety, honesty, or source-grounding.
- If evidence strictness is strict, be clearer about what is supported vs only plausible.
- If challenge style is direct, push back plainly while keeping the user's agency.
- If answer style is concise, be brief; if detailed, give more context.

Learned user preferences:
{preference_context}

Recent conversation:
{history_text}

User question:
{question}

Relevant saved memories:
{evidence_text}

Stored relationships:
{relations_text}
"""


def _build_conversation_prompt(
    *,
    message: str,
    history: list[ConversationTurn],
    preference_context: str,
) -> str:
    history_text = "\n".join(
        f"{turn.role}: {turn.content}" for turn in history[-8:]
    ) or "No earlier turns."
    return f"""Reply to the user's latest message as Crowscap's normal conversational assistant.

Return JSON:
{{
  "reply": "a natural, useful reply"
}}

Rules:
- This is normal chat, not a saved-memory answer.
- Do not mention saved memories, sources, vector search, recall, or knowledge cards unless the recent conversation contains a turn beginning "Immediate context from the source the user just saved" and the latest message is clearly a short follow-up to that just-saved source.
- Do not say you saved anything.
- For definition questions, define the term directly in ordinary language. If useful, connect it to the immediately preceding turn only.
- For short follow-ups such as "don't you think?", "what do you mean?", "why?", or "tell me more", answer from the last few turns first. Do not reach into older saved memory unless it was explicitly provided as immediate context.
- Do not include audit-style sections such as "What is still missing", "Ideas worth comparing", or "Useful next move" in normal chat.
- If the user asks for advice, answer directly like a thoughtful assistant.
- Keep the tone warm, clear, and practical.
- If the user asks to save, remember, or remind them, say you can do that when they state exactly what to save or when to remind them.
- Follow the learned user preferences when they do not conflict with honesty or usefulness.
- If answer style is concise, be brief; if detailed, add context.
- If challenge style is direct, push back plainly when the user's idea needs it.

Learned user preferences:
{preference_context}

Recent conversation:
{history_text}

Latest user message:
{message}
"""


CHAT_ROUTER_SYSTEM_PROMPT = """You route messages for Crowscap, a conversational second brain.
Return only valid JSON. Be conservative about saving: ordinary chat must remain ordinary chat."""


CHAT_SYNTHESIS_SYSTEM_PROMPT = """You are Crowscap's source-aware conversational intelligence.
Return only valid JSON. Help the user understand, question, and use what they have learned without creating false certainty."""


CHAT_CONVERSATION_SYSTEM_PROMPT = """You are Crowscap's normal chat mode.
Return only valid JSON. Answer like a helpful conversational assistant without using saved-memory context."""
