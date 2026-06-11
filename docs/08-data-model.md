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
Stores recall cadence, capture defaults, and notification preferences.

Fields:
- id
- user_id
- recall_frequency
- preferred_review_time
- default_capture_intent
- created_at
- updated_at

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

### memory_relations

Purpose:
Stores edges between memory atoms.

Fields:
- id
- user_id
- source_memory_id
- target_memory_id
- relation_type: supports, challenges, contradicts, depends_on_context, updates, repeats, illustrates, action_gap
- strength: low, medium, high
- explanation
- created_by: system, user
- created_at

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
- vector index on memory_embeddings.embedding
- unique or hash index for sources.extracted_text_hash

## Data Retention Rules

- Raw source snapshots are retained unless user deletes the source.
- Archived memories remain searchable only if user includes archived items.
- Deleted memories should be soft-deleted first, then hard-delete through a retention job if needed.
- User export/delete should be planned before public release.

