# Hackathon Strategy

Last verified: 2026-06-11.

## Official Constraint Summary

Source: https://qwencloud-hackathon.devpost.com/rules

Submission deadline:
- July 9, 2026 at 2:00 PM PDT.
- July 9, 2026 at 10:00 PM WAT/Lagos.

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

Do not position Crowscap as "a personal knowledge base that indexes everything you share." That is already listed as a project inspiration. Our differentiation is the memory lifecycle:

```text
Saved content -> structured memory -> source strength -> tension detection -> recall -> knowledge audit -> action gap
```

Winning frame:

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

## Engineering Depth Angles

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

## Demo Story

Use one clean story under 3 minutes.

1. Show the graveyard problem briefly: many saved links and notes that never became usable.
2. Capture a messy real input: a YouTube transcript, article, or pasted book excerpt.
3. Show Crowscap extracting memory atoms with labels like claim, principle, example, action, question.
4. Show source confidence and why it is not treated as absolute truth.
5. Show tension detection between two saved startup ideas.
6. Ask: "What do I seem to know about distribution?"
7. Show the audit: repeated beliefs, strongest sources, weak assumptions, tensions, unapplied knowledge.
8. Show one generative recall/application question.
9. End with evaluation: atomic retrieval uses less context and returns more useful memories than naive RAG.

## Do Not Overbuild

The hackathon does not need every capture surface. It needs the core memory loop to be excellent.

Build first:
- Web capture.
- Backend processing.
- Memory storage.
- Recall.
- Audit.
- Evaluation.

Mention later:
- Browser extension.
- Mobile share sheet.
- WhatsApp/Telegram.
- Kindle/Readwise import.
- Ambient browser capture.
- Knowledge gap content discovery.

