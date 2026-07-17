# Data Model

## Model Philosophy

Store raw sources separately from extracted memory atoms. The source is evidence. The memory atom is the usable unit.

## Tables

### users

Purpose:
Stores user accounts and preferences.

Fields:
- id
- email
- display_name
- created_at
- updated_at

### user_preferences

Purpose:
Stores durable user preferences for how Crowscap should behave. This is not semantic knowledge memory. It is the user's learning/control profile.

Fields:
- id
- user_id
- profile_key
- preferred_review_time
- recall_frequency
- answer_style: concise, balanced, detailed
- evidence_strictness: relaxed, balanced, strict
- challenge_style: gentle, balanced, direct
- memory_density: compact, balanced, rich
- notification_preference
- topics_of_interest
- source_preferences
- updated_from_message_id
- metadata_json
- created_at
- updated_at

Current implementation:
The preference profile is updated from two signal tiers.

High-confidence explicit preferences come from direct user language. Examples:

- "I prefer short answers" -> `answer_style=concise`
- "Challenge my assumptions more" -> `challenge_style=direct`
- "I care mostly about startups and product" -> adds topics of interest
- "Do not show weak YouTube advice unless there is evidence" -> source preference plus stricter evidence handling

Lower-confidence autonomous signals come from accumulated behavior:

- Repeated capture topics -> inferred topics of interest
- Archive events -> topics or memory types to deprioritize
- Recall reviews -> memory types the user seems to retain well
- Source mix -> transparency about the user's saved source patterns

The profile is used by chat synthesis, belief audits, and recall prompt generation.

### sources

Purpose:
Stores original artifact metadata.

Fields:
- id
- user_id
- source_type: url, pdf, text, youtube, screenshot, note
- original_url
- title
- author
- publisher
- published_at
- captured_snapshot_uri
- raw_text_uri
- raw_text: exact text submitted by the user for source fidelity and reference
- extracted_text_hash
- metadata_json
- created_at
- updated_at

### captures

Purpose:
Represents the user's act of saving something.

Fields:
- id
- user_id
- source_id
- user_note
- user_intent_text
- inferred_intents: array/json
- status: queued, processing, ready, failed, archived
- failure_reason
- created_at
- updated_at

### extraction_jobs

Purpose:
Tracks background processing.

Fields:
- id
- capture_id
- status: queued, running, succeeded, failed, retrying
- step
- attempts
- error_code
- error_message_safe
- started_at
- finished_at
- created_at
- updated_at

### source_chunks

Purpose:
Stores cleaned chunks used for extraction and traceability.

Fields:
- id
- source_id
- chunk_index
- text
- token_estimate
- location_json
- extraction_method
- created_at

### memories

Purpose:
Stores atomic memories.

Fields:
- id
- user_id
- source_id
- capture_id
- source_chunk_id
- memory_type: claim, principle, definition, example, warning, action, question, quote, reference, intention
- epistemic_label
- content
- summary
- confidence: low, medium, high, unknown
- confidence_reason
- source_strength: weak, moderate, strong, unknown
- importance_score
- decay_score
- status: active, archived, merged, deleted
- canonical_memory_id
- next_review_at
- last_reviewed_at
- review_count
- recall_score
- created_at
- updated_at

### memory_embeddings

Purpose:
Stores vector embeddings for memory retrieval.

Fields:
- id
- memory_id
- model
- dimensions
- embedding
- created_at

Note:
Use `text-embedding-v4`. Qwen docs list 1024 as default dimensions and 8192 max tokens for text embeddings. Choose dimensions deliberately before creating the index.

Phase 0 note:
The local SQLite implementation stores embeddings on `memories.embedding_json`. PostgreSQL keeps that portable copy and also writes the same vector to `memories.embedding_vector vector(1024)` for indexed pgvector search.

### memory_relations

Purpose:
Stores edges between memory atoms.

Fields:
- id
- user_id
- source_memory_id
- target_memory_id
- relation_type: confirms, conflicts, tension, extends, qualifies
- strength: weak, moderate, strong, unknown
- explanation
- created_by: qwen, system, user, test
- created_at

Phase 0 note:
The local implementation stores directed edges from a newly captured memory to older candidate memories. It uses semantic similarity first, then one batched Qwen JSON classification call per capture. Candidate memories from the same capture are excluded so one source is not treated as an independent viewpoint. Meta memories such as `intention`, `question`, and `reference` are not automatically relationship-scanned.

Relationship classifications must cite exact evidence phrases from both memories. The backend rejects weak results and any result whose evidence does not appear verbatim in the corresponding memory. This protects the graph from plausible-sounding but unsupported connections.

### memory_perspective_notes

Purpose:
Stores delayed, non-judgmental prompts linked to under-evidenced or one-sided memories. These notes are Crowscap's "ignorance gap" surface. They ask the user to consider a counterexample, boundary condition, or stronger source later. They do not automatically rewrite the user's memory.

Fields:
- id
- user_id
- memory_id
- status: queued, surfaced, accepted, dismissed
- perspective_type: counterpoint, nuance, evidence_gap
- title
- content
- suggested_query
- confidence
- surface_after_at
- surfaced_at
- accepted_at
- dismissed_at
- created_by
- metadata_json
- created_at
- updated_at

Creation rule:
Crowscap queues notes for claim-like memories such as `claim`, `principle`, `framework`, `prediction`, and `warning` when they are not strongly supported or are labeled as opinion, advice, prediction, framework, or unresolved. High-confidence memories from strong sources are skipped.

User-control rule:
Accepting a note marks it useful but does not create a new memory automatically. Dismissing a note stops it from surfacing.

### recall_prompts

Purpose:
Stores prompts generated for memories.

Fields:
- id
- user_id
- memory_id
- prompt_type: explain, defend, apply, compare, verify, contextualize
- prompt_text
- due_at
- priority_score
- status: due, scheduled, completed, snoozed, archived
- created_at
- updated_at

### recall_attempts

Purpose:
Stores user answers and review outcomes.

Fields:
- id
- recall_prompt_id
- user_answer
- self_rating
- model_feedback
- score
- next_due_at
- created_at

Phase 0 implementation:
The current table is named `recall_reviews` because prompts are generated from the
memory at request time rather than stored separately. It records:

- memory_id
- answer_text
- self_rating
- evaluation_score
- rating
- feedback
- understanding_summary
- knowledge_gaps
- context_to_consider
- next_question
- next_review_at
- created_at

The corresponding memory row is updated in the same transaction with
`last_reviewed_at`, `review_count`, `recall_score`, and `next_review_at`.

### audits

Purpose:
Stores generated topic audits for history and demo repeatability.

Fields:
- id
- user_id
- topic_query
- apparent_stance
- repeated_ideas_json
- strongest_sources_json
- weakest_assumptions_json
- tensions_json
- action_gaps_json
- memory_ids_used
- created_at

### actions

Purpose:
Stores applications or experiments linked to memories.

Fields:
- id
- user_id
- memory_id
- title
- description
- status: proposed, planned, doing, done, dismissed
- due_at
- completed_at
- created_at
- updated_at

### tags

Purpose:
Topic tags or user-created labels.

Fields:
- id
- user_id
- name
- created_at

### memory_tags

Purpose:
Many-to-many relationship between memories and tags.

Fields:
- memory_id
- tag_id

## Indexes

Recommended:
- memories(user_id, status)
- captures(user_id, status, created_at)
- recall_prompts(user_id, status, due_at)
- memory_relations(user_id, source_memory_id)
- memory_relations(user_id, target_memory_id)
- memory_perspective_notes(user_id, status, surface_after_at)
- vector index on memory_embeddings.embedding
- unique or hash index for sources.extracted_text_hash

## Data Retention Rules

- Raw source snapshots are retained unless user deletes the source.
- Archived memories remain searchable only if user includes archived items.
- Dismissed perspective notes remain as audit trail but should not surface again.
- Deleted memories should be soft-deleted first, then hard-delete through a retention job if needed.
- User export/delete should be planned before public release.
