# Chat Routing And Trust

Crowscap should not treat every message as a memory operation. The chat layer has three trust boundaries:

1. Normal conversation stays normal.
2. Factual questions about the current chat are answered from stored chat messages, not generated from memory search.
3. External sources are saved only when the user clearly intends to save them.

## Current-Chat Facts

Questions such as "what was my first message?", "what did I just say?", and "have I thanked you in this chat?" are session facts. They are resolved from the persisted `messages` rows for the active conversation.

The answer should be exact and brief. It should not include memory cards, public evidence, "what is missing", or idea-comparison sections. If the relevant message is not found, Crowscap should say it cannot find it rather than guessing.

## URL Capture Safety

A bare URL in chat is not enough evidence that the user wants permanent memory extraction. Bare URLs now create a confirmation response:

> I found this link. I have not saved it yet. Reply "save this link" if you want Crowscap to read and remember it.

If the user explicitly says "save this", "remember this", "read later", "capture this", or similar around the URL, Crowscap captures it immediately.

This keeps accidental links out of long-term memory while preserving the fast capture flow for intentional saves.

## Why This Exists

The product promise is not just "Crowscap remembers." It is "Crowscap remembers correctly, with user intent." Exact conversation facts require retrieval. Knowledge synthesis requires RAG. Capture requires intent. Mixing those paths creates confident wrongness and memory pollution.
