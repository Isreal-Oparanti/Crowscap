# Hackathon Strategy



## Official Constraint Summary

Source: https://qwencloud-hackathon.devpost.com/rules

Submission deadline:
- July 9, 2026 at 2:00 PM PDT.
- July 20, 2026 at 10:00 PM WAT/Lagos.

Track:
- Track 1 - MemoryAgent.

Track requirement:
- Build an agent with persistent memory.
- It should autonomously accumulate experience.
- It should remember preferences or user context across sessions.
- It should improve decisions across multi-turn or cross-session interactions.
- It should focus on efficient storage/retrieval, timely forgetting of outdated information, and recall of critical memories within limited context windows.

Submission requirements:
- Public code repository.
- Open-source license visible at the top of the repository page.
- Text description of features and functionality.
- Proof that backend is running on Alibaba Cloud.
- Link to a code file demonstrating use of Alibaba Cloud services/APIs.
- Architecture diagram showing frontend, backend, database, and Qwen Cloud connection.
- Demo video less than 3 minutes. Judges are not required to watch beyond 3 minutes.
- Track identification.
- Optional public blog/social post for bonus prize.

Judging:
- Innovation and AI Creativity: 30%.
- Technical Depth and Engineering: 30%.
- Problem Value and Impact: 25%.
- Presentation and Documentation: 15%.

## Strategic Positioning

We are not position Crowscap as "a personal knowledge base that indexes everything you share." That is already listed as a project inspiration. Our differentiation is the memory lifecycle:

```text
Saved content -> structured memory -> source strength -> tension detection -> recall -> knowledge audit -> action gap
```

OUR frame:

"Most tools help you save information. Crowscap helps information become memory you can question and use."

## Hackathon Hero Feature

The hero feature is the Knowledge Audit.

Example query:

"What do I seem to know about startup distribution?"

Output:
- Repeated beliefs.
- Strongest supporting sources.
- Weakest assumptions.
- Tensions or context-dependent disagreements.
- Memories that have been saved repeatedly but not acted on.
- One sharp recall or application prompt.

This is more memorable than a graph and more differentiated than semantic search.

## Engineering Angles

1. Structured atomic memory extraction:
   Use Qwen Cloud structured output and Pydantic validation.

2. Multi-stage retrieval:
   Store atomic memories with embeddings, retrieve top candidates, optionally rerank, then synthesize.

3. Tension detection:
   Run relation classification between new memories and semantically nearby existing memories.

4. Multi-signal recall scoring:
   Combine recall performance, importance, source strength, fragility/tension, topic recency, user intent, and action gap.

5. Forgetting/archiving:
   Archive duplicate, low-value, stale, ignored, or superseded memories.

6. MCP:
   Expose Crowscap memory tools through an MCP server so agents can call `capture_memory`, `search_memory`, `get_due_recalls`, `audit_topic`, and `archive_memory`.

7. Evaluation harness:
   Compare Crowscap atomic retrieval against naive document chunk retrieval.


## Building Strategy

The hackathon does not need every capture surface. It needs the core memory loop to be excellent.

Build first:
- Web capture.
- Backend processing.
- Memory storage.
- Recall.
- Audit.
- Evaluation.

Long term improvement:
- Browser extension.
- knowlegde gap surface
- Mobile share sheet.
- WhatsApp/Telegram.
- Kindle/Readwise import.
- Ambient browser capture.
- Knowledge gap content discovery.

