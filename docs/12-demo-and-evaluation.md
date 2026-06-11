# Demo and Evaluation

## Demo Goal

In less than 3 minutes, judges should understand:

- the problem is real.
- Crowscap is not a bookmark app.
- the system uses Qwen Cloud deeply.
- the architecture has production thinking.
- the memory engine beats naive retrieval in a visible way.

## Demo Dataset

Use three to five sources around one topic:

Topic: startup distribution.

Possible source types:
- YouTube transcript about sales/distribution.
- Article or blog post about early customer discovery.
- Book excerpt or pasted highlight.
- Contrasting advice about product-led growth.
- User note: "I keep hearing distribution matters but have not run experiments."

Avoid copyrighted long excerpts in the video. Use short snippets or original notes where possible.

## Demo Script

0:00-0:15
Show the problem: saved links/notes are a graveyard.

0:15-0:40
Capture one messy source. Add natural intent: "I need to apply this to my startup."

0:40-1:10
Show extraction result:
- claim.
- principle.
- example.
- action.
- question.
- source confidence.

1:10-1:35
Show relation/tension detection:
- "This supports your earlier memory."
- "This depends on context."
- "This is repeated but not acted on."

1:35-2:15
Show Knowledge Audit:
"What do I seem to know about startup distribution?"

Output:
- apparent stance.
- strongest sources.
- weakest assumptions.
- tensions.
- action gaps.
- suggested application prompt.

2:15-2:40
Show recall/application prompt:
"You saved this idea several times. What distribution experiment are you running this week?"

2:40-2:55
Show evaluation:
Crowscap retrieves atomic memories and uses less context than naive chunk retrieval.

2:55-3:00
Close with product promise and architecture diagram glimpse.

## Evaluation Harness

Compare:

Naive RAG:
- chunk sources.
- embed chunks.
- retrieve chunks by query.
- synthesize from chunks.

Crowscap:
- extract atomic memories.
- embed memories.
- retrieve memory atoms.
- include relation edges.
- synthesize audit.

Metrics:
- context tokens used.
- relevant memory atoms retrieved.
- duplicate/noise count.
- source coverage.
- relation/tension surfaced.
- answer usefulness rating.

Example evaluation query:

"What do I seem to know about distribution, and what have I not acted on?"

Naive RAG likely returns broad chunks.
Crowscap should return:
- repeated principle.
- action memory.
- action gap relation.
- source confidence.
- tension/context note.

## Evaluation Output Format

```json
{
  "query": "What do I seem to know about distribution?",
  "naive_rag": {
    "context_tokens": 4200,
    "relevant_items": 4,
    "duplicates": 3,
    "surfaced_tensions": 0
  },
  "crowscap": {
    "context_tokens": 1100,
    "relevant_items": 8,
    "duplicates": 0,
    "surfaced_tensions": 2,
    "action_gaps": 1
  }
}
```

Do not fabricate final metrics in the submission. Run the harness on fixed demo data and report actual numbers.

## Submission Checklist

- Public repo.
- LICENSE file.
- Working install instructions.
- `.env.example`.
- Architecture diagram.
- Backend deployment proof on Alibaba Cloud.
- Code file demonstrating Alibaba Cloud service/API usage.
- Demo video under 3 minutes.
- Devpost description.
- Track: MemoryAgent.
- Optional blog/social post.

