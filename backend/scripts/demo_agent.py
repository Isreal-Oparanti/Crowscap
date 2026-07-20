"""
Crowscap MCP Demo Agent
=======================
Demonstrates a complete agentic loop using the Crowscap MCP server.

This script connects to the MCP SSE endpoint and chains seven tool calls
to show the full lifecycle:

  1. capture_text      — agent saves a new note to memory (WRITE)
  2. search_memory     — agent retrieves related memories by meaning (READ)
  3. get_due_recalls   — agent checks what needs reviewing (READ)
  4. submit_quick_recall — agent marks a memory as still-relevant (WRITE)
  5. audit_belief      — agent synthesises what the user appears to believe (READ)
  6. get_user_preferences — agent reads the learned behaviour profile (READ)
  7. archive_memory    — agent archives a memory the user dismissed (WRITE)

The script uses the MCP Python client over SSE so it exercises the real
protocol stack, not just the Python function calls.

Usage
-----
Start the MCP server in one terminal:

    cd backend
    .\\.venv\\Scripts\\python -m app.mcp.server

Then run the demo in another terminal:

    cd backend
    .\\.venv\\Scripts\\python scripts/demo_agent.py

To target the live deployed server instead of local:

    .\\.venv\\Scripts\\python scripts/demo_agent.py --url https://api.crowscap.xyz/mcp/sse

Options
-------
--url       MCP SSE endpoint URL (default: http://127.0.0.1:8010/mcp/sse)
--user-id   Optional user_id to scope all tool calls
--quiet     Print only the final summary, not each step

Exit codes
----------
0  All tool calls succeeded.
1  One or more tool calls failed (error details are printed).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# ---------------------------------------------------------------------------
# MCP client import — requires the `mcp` package already installed as a
# dependency of the Crowscap backend.
# ---------------------------------------------------------------------------
try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
except ImportError as exc:
    print(
        "ERROR: The mcp package is not available. "
        "Run: pip install mcp\n"
        f"Details: {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

import asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pretty(label: str, result: Any, quiet: bool) -> None:
    if quiet:
        return
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")
    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result)


def _extract_json(call_result: Any) -> dict[str, Any]:
    """Pull the dict payload out of an MCP CallToolResult."""
    # The MCP SDK returns a CallToolResult with a `content` list.
    # Each item is a TextContent whose `.text` is a JSON string.
    content = getattr(call_result, "content", [])
    if content:
        raw = getattr(content[0], "text", "{}")
        return json.loads(raw)
    return {}


# ---------------------------------------------------------------------------
# Demo loop
# ---------------------------------------------------------------------------

async def run_demo(url: str, user_id: str | None, quiet: bool) -> int:
    errors: list[str] = []

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ------------------------------------------------------------------
            # Step 1: capture_text (WRITE)
            # ------------------------------------------------------------------
            print("\n🔵 Step 1/7 — capture_text (WRITE)")
            capture_args: dict[str, Any] = {
                "content": (
                    "Founders who nail distribution before product-market fit often discover "
                    "that the right channel shapes what the product needs to become. "
                    "This is the opposite of the build-first instinct."
                ),
                "intent_text": "Remember for go-to-market planning.",
                "source_title": "Crowscap MCP demo note",
            }
            if user_id:
                capture_args["user_id"] = user_id

            try:
                result = await session.call_tool("capture_text", capture_args)
                capture_payload = _extract_json(result)
                _pretty("capture_text result", capture_payload, quiet)
                memory_count = capture_payload.get("memory_count", 0)
                captured_memory_ids = [m["id"] for m in capture_payload.get("memories", [])]
                print(f"  ✅ Saved {memory_count} memory atom(s). IDs: {captured_memory_ids}")
            except Exception as exc:
                msg = f"capture_text failed: {exc}"
                print(f"  ❌ {msg}")
                errors.append(msg)
                captured_memory_ids = []

            # ------------------------------------------------------------------
            # Step 2: search_memory (READ)
            # ------------------------------------------------------------------
            print("\n🔵 Step 2/7 — search_memory (READ)")
            search_args: dict[str, Any] = {
                "query": "how should founders approach distribution?",
                "limit": 5,
                "min_score": 0.1,
            }
            if user_id:
                search_args["user_id"] = user_id

            try:
                result = await session.call_tool("search_memory", search_args)
                search_payload = _extract_json(result)
                _pretty("search_memory result", search_payload, quiet)
                returned = search_payload.get("returned_count", 0)
                print(f"  ✅ Found {returned} matching memory(-ies).")
            except Exception as exc:
                msg = f"search_memory failed: {exc}"
                print(f"  ❌ {msg}")
                errors.append(msg)

            # ------------------------------------------------------------------
            # Step 3: get_due_recalls (READ)
            # ------------------------------------------------------------------
            print("\n🔵 Step 3/7 — get_due_recalls (READ)")
            recall_args: dict[str, Any] = {"limit": 3}
            if user_id:
                recall_args["user_id"] = user_id

            try:
                result = await session.call_tool("get_due_recalls", recall_args)
                due_payload = _extract_json(result)
                _pretty("get_due_recalls result", due_payload, quiet)
                due_count = due_payload.get("due_count", 0)
                due_memory_ids = [m["memory_id"] for m in due_payload.get("memories", [])]
                print(f"  ✅ {due_count} item(s) due. Memory IDs: {due_memory_ids}")
            except Exception as exc:
                msg = f"get_due_recalls failed: {exc}"
                print(f"  ❌ {msg}")
                errors.append(msg)
                due_memory_ids = []

            # ------------------------------------------------------------------
            # Step 4: submit_quick_recall (WRITE)
            # Agent acknowledges the first due memory as still-relevant.
            # ------------------------------------------------------------------
            target_id = (due_memory_ids or captured_memory_ids or [None])[0]
            if target_id:
                print(f"\n🔵 Step 4/7 — submit_quick_recall (WRITE) for memory {target_id}")
                quick_args: dict[str, Any] = {
                    "memory_id": target_id,
                    "action": "still_relevant",
                }
                if user_id:
                    quick_args["user_id"] = user_id

                try:
                    result = await session.call_tool("submit_quick_recall", quick_args)
                    quick_payload = _extract_json(result)
                    _pretty("submit_quick_recall result", quick_payload, quiet)
                    print(
                        f"  ✅ Recall recorded. review_count={quick_payload.get('review_count')} "
                        f"recall_score={quick_payload.get('recall_score'):.3f} "
                        f"next_due={quick_payload.get('next_due_at', '')[:10]}"
                    )
                except Exception as exc:
                    msg = f"submit_quick_recall failed: {exc}"
                    print(f"  ❌ {msg}")
                    errors.append(msg)
            else:
                print("\n⚪ Step 4/7 — submit_quick_recall skipped (no memory ID available)")

            # ------------------------------------------------------------------
            # Step 5: audit_belief (READ)
            # ------------------------------------------------------------------
            print("\n🔵 Step 5/7 — audit_belief (READ)")
            audit_args: dict[str, Any] = {
                "topic": "startup distribution strategy",
                "include_public_evidence": False,
                "memory_limit": 5,
            }
            if user_id:
                audit_args["user_id"] = user_id

            try:
                result = await session.call_tool("audit_belief", audit_args)
                audit_payload = _extract_json(result)
                _pretty("audit_belief result", audit_payload, quiet)
                print(
                    f"  ✅ Audit complete. confidence={audit_payload.get('confidence')} "
                    f"memories_used={audit_payload.get('memory_count')}"
                )
            except Exception as exc:
                msg = f"audit_belief failed: {exc}"
                print(f"  ❌ {msg}")
                errors.append(msg)

            # ------------------------------------------------------------------
            # Step 6: get_user_preferences (READ)
            # ------------------------------------------------------------------
            print("\n🔵 Step 6/7 — get_user_preferences (READ)")
            pref_args: dict[str, Any] = {}
            if user_id:
                pref_args["user_id"] = user_id

            try:
                result = await session.call_tool("get_user_preferences", pref_args)
                pref_payload = _extract_json(result)
                _pretty("get_user_preferences result", pref_payload, quiet)
                print(
                    f"  ✅ Preferences loaded. answer_style={pref_payload.get('answer_style')} "
                    f"recall_frequency={pref_payload.get('recall_frequency')}"
                )
            except Exception as exc:
                msg = f"get_user_preferences failed: {exc}"
                print(f"  ❌ {msg}")
                errors.append(msg)

            # ------------------------------------------------------------------
            # Step 7: archive_memory (WRITE)
            # Agent archives the captured memory to show the full lifecycle.
            # ------------------------------------------------------------------
            archive_target = (captured_memory_ids or [None])[0]
            if archive_target:
                print(f"\n🔵 Step 7/7 — archive_memory (WRITE) for memory {archive_target}")
                archive_args: dict[str, Any] = {
                    "memory_id": archive_target,
                    "reason": "superseded",
                    "note": "Demo agent archived this after confirming recall.",
                }
                if user_id:
                    archive_args["user_id"] = user_id

                try:
                    result = await session.call_tool("archive_memory", archive_args)
                    archive_payload = _extract_json(result)
                    _pretty("archive_memory result", archive_payload, quiet)
                    print(
                        f"  ✅ Memory archived. "
                        f"previous_status={archive_payload.get('previous_status')} → "
                        f"new_status={archive_payload.get('new_status')}"
                    )
                except Exception as exc:
                    msg = f"archive_memory failed: {exc}"
                    print(f"  ❌ {msg}")
                    errors.append(msg)
            else:
                print("\n⚪ Step 7/7 — archive_memory skipped (no captured memory ID available)")

    # --------------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------------
    print(f"\n{'═' * 60}")
    if errors:
        print(f"  DEMO FINISHED WITH {len(errors)} ERROR(S):")
        for err in errors:
            print(f"    • {err}")
        print(f"{'═' * 60}\n")
        return 1
    else:
        print("  DEMO COMPLETE — all tool calls succeeded ✅")
        print("  The full agent loop (read + write) ran end-to-end over MCP/SSE.")
        print(f"{'═' * 60}\n")
        return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Crowscap MCP demo agent")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8010/mcp/sse",
        help="MCP SSE endpoint URL (default: http://127.0.0.1:8010/mcp/sse)",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Optional user_id to scope all tool calls",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the final summary, not each tool result",
    )
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║          Crowscap MCP Demo Agent                        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Endpoint : {args.url:<46}║")
    print(f"║  User ID  : {str(args.user_id or '(none)'):<46}║")
    print("╚══════════════════════════════════════════════════════════╝")

    exit_code = asyncio.run(run_demo(url=args.url, user_id=args.user_id, quiet=args.quiet))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
