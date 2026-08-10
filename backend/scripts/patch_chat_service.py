"""
Patch script: applies the 3 context-fix changes to chat_service.py in one shot.

Run from the repo root:
    python backend/scripts/patch_chat_service.py
"""
import pathlib
import sys

TARGET = pathlib.Path("backend/app/services/chat_service.py")

# ── 1. Patch: Remove _asks_recent_source_question from _grounded_local_conversation_reply ─────────
OLD_GROUNDED = """\
    if _asks_recent_source_question(normalized):
        if reply := _recent_link_content_reply(db=db, conversation=conversation, user_id=user_id):
            return reply

    if _asks_about_recent_capture(normalized):
        if reply := _recent_link_content_reply(
            db=db,
            conversation=conversation,
            user_id=user_id,
            require_url=False,
        ):
            return reply"""

NEW_GROUNDED = """\
    # _asks_recent_source_question() was intentionally removed here.
    # It was too broad: it matched compound follow-up questions like
    # "What's the video about and the original movie?" and returned a
    # hardcoded memory-card template, bypassing the LLM entirely.
    # Those questions now fall through to the LLM path where
    # _model_prompt_history() already injects the recent capture context
    # as a synthetic assistant turn, and conversation_responder.respond()
    # produces a real answer that addresses the actual question.

    # Only intercept the simplest exact deictic queries (short, unambiguous
    # patterns like "what's the above about", "what was that about").
    if _asks_about_recent_capture(normalized):
        if reply := _recent_link_content_reply(
            db=db,
            conversation=conversation,
            user_id=user_id,
            require_url=False,
        ):
            return reply"""

# ── 2. Patch: Replace "recent" action dispatch with LLM-backed version ─────────────────────────
OLD_RECENT = """\
    if route.action == "recent":
        reply = _recent_link_content_reply(
            db=db,
            conversation=conversation,
            user_id=user_id,
            require_url=False,
        )
        if reply is None:
            reply = (
                "I do not see anything saved in this chat yet, so there is nothing recent "
                "for me to describe. Save a link or note first and ask me again."
            )
        logger.info("\\u2705 chat.message.complete action=recent saved=False")
        response = ChatResponse(action="conversation", message=reply, saved=False)
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )"""

NEW_RECENT = """\
    if route.action == "recent":
        # Inject recent capture context into model_history so the LLM can
        # actually answer the user's specific question rather than returning
        # the same hardcoded memory-card template every time.
        recent_capture = _latest_captured_source_from_conversation(
            db=db,
            conversation=conversation,
            user_id=user_id,
            source_type_hint=None,
        )
        enriched_history = model_history
        if recent_capture is not None:
            capture_turn = _recent_capture_context_turn(recent_capture)
            if capture_turn is not None:
                enriched_history = [capture_turn, *model_history]

        try:
            reply = conversation_responder.respond(
                message=payload.message,
                history=enriched_history,
                preferences=preferences,
            )
        except Exception:
            # Fallback to the template only if the LLM call fails
            logger.exception("\\u26a0\\ufe0f chat.recent.llm_fallback conversation_id=%s", conversation.id)
            reply = _recent_link_content_reply(
                db=db,
                conversation=conversation,
                user_id=user_id,
                require_url=False,
            ) or (
                "I do not see anything saved in this chat yet, so there is nothing recent "
                "for me to describe. Save a link or note first and ask me again."
            )
        if reply is None:
            reply = (
                "I do not see anything saved in this chat yet, so there is nothing recent "
                "for me to describe. Save a link or note first and ask me again."
            )
        logger.info("\\u2705 chat.message.complete action=recent saved=False")
        response = ChatResponse(action="conversation", message=reply, saved=False)
        response = _with_preference_learning(response, preference_learning)
        return _persist_assistant_response(
            db=db,
            conversation=conversation,
            user_message=user_message,
            response=response,
            user_id=user_id,
        )"""

# ── 3. Patch: Expand local_reference_words in _should_include_recent_capture_context ───────────
OLD_REFWORDS = """\
    local_reference_words = {
        "this",
        "that",
        "it",
        "these",
        "those",
        "there",
        "above",
        "previous",
        "last",
        "deep",
        "interesting",
        "serious",
        "true",
        "right",
        "wrong",
        "mean",
        "means",
        "meaning",
    }
    if len(words) <= 12 and (
        _is_short_conversation_followup(normalized)
        or any(word in local_reference_words for word in words)
    ):
        return True
    return False"""

NEW_REFWORDS = """\
    local_reference_words = {
        "this",
        "that",
        "it",
        "these",
        "those",
        "there",
        "above",
        "previous",
        "last",
        "deep",
        "interesting",
        "serious",
        "true",
        "right",
        "wrong",
        "mean",
        "means",
        "meaning",
        # Source content query words — ensures compound follow-up questions
        # about a just-saved video/link/article inject the capture context turn
        # into the LLM prompt so it can answer the actual question.
        "video",
        "link",
        "url",
        "article",
        "page",
        "short",
        "about",
        "original",
        "movie",
        "film",
        "content",
        "what",
        "explain",
        "summarize",
        "summarise",
        "say",
        "says",
        "tells",
        "discuss",
        "cover",
        "covers",
    }
    if any(word in local_reference_words for word in words):
        return True
    if len(words) <= 12 and _is_short_conversation_followup(normalized):
        return True
    return False"""


def apply_patch(text: str, old: str, new: str, label: str) -> str:
    # Normalize line endings for matching
    normalized_text = text.replace("\r\n", "\n")
    normalized_old = old.replace("\r\n", "\n")
    if normalized_old not in normalized_text:
        print(f"ERROR: Could not find patch target for '{label}'")
        print("Searching for first 3 lines...")
        first_lines = "\n".join(normalized_old.splitlines()[:3])
        if first_lines in normalized_text:
            print(f"  → First lines found but full match failed. Check whitespace.")
        else:
            print(f"  → First lines not found either.")
        sys.exit(1)
    result = normalized_text.replace(normalized_old, new.replace("\r\n", "\n"), 1)
    print(f"[OK] Patch applied: {label}")
    return result


def main():
    text = TARGET.read_text(encoding="utf-8")

    text = apply_patch(text, OLD_GROUNDED, NEW_GROUNDED,
                       "Remove _asks_recent_source_question from _grounded_local_conversation_reply")
    text = apply_patch(text, OLD_RECENT, NEW_RECENT,
                       "Replace 'recent' action dispatch with LLM-backed version")
    text = apply_patch(text, OLD_REFWORDS, NEW_REFWORDS,
                       "Expand local_reference_words in _should_include_recent_capture_context")

    TARGET.write_text(text, encoding="utf-8")
    print(f"\n[DONE] All 3 patches applied successfully to {TARGET}")


if __name__ == "__main__":
    main()
