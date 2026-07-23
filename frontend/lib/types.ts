export type Relationship = {
  related_memory_id: string;
  relationship_type:
    | "confirms"
    | "conflicts"
    | "tension"
    | "extends"
    | "qualifies"
    | "unrelated";
  strength: "weak" | "moderate" | "strong";
  explanation: string | null;
};

export type MemoryCard = {
  id: string;
  source_type: string;
  memory_type: string;
  epistemic_label: string | null;
  content: string;
  summary: string | null;
  confidence: string;
  confidence_reason: string | null;
  source_strength: string;
  embedding_dimensions: number | null;
  relationships: Relationship[];
};

export type CaptureResponse = {
  capture_id: string;
  source_id: string;
  source_type: string;
  source_title: string | null;
  original_content: string | null;
  status: string;
  inferred_intents: string[];
  memories: MemoryCard[];
  metadata_json?: Record<string, unknown> | null;
};

export type ProcessingJobResponse = {
  id: string;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "failed" | "retrying" | string;
  step: string;
  attempts: number;
  capture_id: string | null;
  source_id: string | null;
  error_code: string | null;
  error_message_safe: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  result: CaptureResponse | null;
};

export type SourceContentResponse = {
  source_id: string;
  source_type: string;
  title: string | null;
  original_url: string | null;
  original_content: string | null;
};

export type ConversationTurn = {
  role: "user" | "assistant";
  content: string;
};

export type UserPreferenceProfile = {
  id: string;
  user_id: string | null;
  preferred_review_time: string | null;
  recall_frequency: "low" | "normal" | "high" | "daily" | "weekly" | null;
  answer_style: "concise" | "balanced" | "detailed" | null;
  evidence_strictness: "relaxed" | "balanced" | "strict";
  challenge_style: "gentle" | "balanced" | "direct";
  memory_density: "compact" | "balanced" | "rich" | null;
  notification_preference: string | null;
  topics_of_interest: string[];
  source_preferences: Record<string, unknown>;
  confidence_scores: Record<string, number>;
  inferred_topics: string[];
  deprioritized_topics: string[];
  deprioritized_memory_types: string[];
  content_affinities: Record<string, unknown>;
  learning_signals: string[];
  last_autonomous_update_at: string | null;
  updated_from_message_id: string | null;
  updated_at: string;
};

export type UserPreferenceLearningResponse = {
  preferences: UserPreferenceProfile;
  updates: string[];
};

export type PerspectiveNote = {
  id: string;
  memory_id: string;
  memory_content: string;
  source_title: string | null;
  status: "queued" | "surfaced" | "accepted" | "dismissed";
  perspective_type: "counterpoint" | "nuance" | "evidence_gap";
  title: string;
  content: string;
  suggested_query: string | null;
  confidence: string;
  surface_after_at: string;
  created_at: string;
};

export type PerspectiveNoteListResponse = {
  count: number;
  notes: PerspectiveNote[];
};

export type ChatResponse = {
  action:
    | "acknowledge"
    | "conversation"
    | "capture"
    | "answer"
    | "audit"
    | "forget"
    | "reminder"
    | "self"
    | "recent";
  message: string;
  conversation_id: string | null;
  user_message_id: string | null;
  assistant_message_id: string | null;
  saved: boolean;
  capture: CaptureResponse | null;
  evidence: SearchResult[];
  knowledge_gaps: string[];
  tensions: string[];
  next_step: string | null;
  audit: BeliefAuditResponse | null;
  reminder: ReminderResponse | null;
  preference_updates: string[];
  preferences: UserPreferenceProfile | null;
};

export type PersistedChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  action: ChatResponse["action"] | null;
  metadata_json: ChatResponse | null;
  created_at: string;
};

export type ConversationResponse = {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  messages: PersistedChatMessage[];
};

export type SearchResult = {
  memory_id: string;
  source_id: string;
  source_type: string;
  source_title: string | null;
  memory_type: string;
  epistemic_label: string | null;
  content: string;
  summary: string | null;
  confidence: string;
  confidence_reason: string | null;
  source_strength: string;
  similarity_score: number;
  embedding_dimensions: number | null;
};

export type SearchResponse = {
  query: string;
  min_score: number;
  candidate_count: number;
  embedded_candidate_count: number;
  returned_count: number;
  top_score: number | null;
  results: SearchResult[];
};

export type PublicEvidenceResult = {
  title: string;
  url: string;
  snippet: string | null;
  source: string | null;
  query: string;
  rank: number | null;
};

export type BeliefAuditResponse = {
  topic: string;
  answer: string;
  current_understanding: string;
  strongest_saved_ideas: string[];
  public_evidence_summary: string;
  unsupported_or_weak_points: string[];
  ideas_to_compare: string[];
  confidence: "low" | "medium" | "high" | "unknown";
  confidence_reason: string;
  next_questions: string[];
  memories: SearchResult[];
  public_evidence: PublicEvidenceResult[];
  public_search_status: "searched" | "no_results" | "disabled" | "failed";
  public_search_message: string | null;
};

export type RecallRelationship = {
  related_memory_id: string;
  related_memory_content: string;
  relationship_type: string;
  strength: string;
  explanation: string | null;
  direction: "incoming" | "outgoing";
};

export type DueRecall = {
  memory_id: string;
  source_id: string;
  source_title: string | null;
  memory_type: string;
  epistemic_label: string | null;
  content: string;
  summary: string | null;
  confidence: string;
  confidence_reason: string | null;
  source_strength: string;
  next_review_at: string;
  last_reviewed_at: string | null;
  review_count: number;
  recall_score: number;
  overdue_seconds: number;
  recall_prompt: string;
  epistemic_caution: string | null;
  surface_reason: string | null;
  relationships: RecallRelationship[];
};

export type DueReminder = {
  reminder_id: string;
  content: string;
  due_at: string;
  overdue_seconds: number;
  save_as_memory: boolean;
  memory_id: string | null;
  status: string;
};

export type DueRecallsResponse = {
  due_count: number;
  now: string;
  memories: DueRecall[];
  reminders: DueReminder[];
};

export type ReminderResponse = {
  id: string;
  content: string;
  due_at: string;
  status: string;
  save_as_memory: boolean;
  memory_id: string | null;
  conversation_id: string | null;
  created_at: string;
};

export type RecallAnswerResponse = {
  review_id: string;
  memory_id: string;
  feedback: string;
  score: number;
  rating: "needs_work" | "partial" | "solid" | "strong";
  understanding_summary: string;
  knowledge_gaps: string[];
  context_to_consider: string[];
  next_question: string | null;
  next_due_at: string;
  review_count: number;
  recall_score: number;
};

export type RecallQuickAction = "still_relevant" | "applied" | "not_now";

export type RecallQuickResponse = {
  memory_id: string;
  action: RecallQuickAction;
  feedback: string;
  next_due_at: string;
  review_count: number;
  recall_score: number;
};
