/**
 * API response types for the Crowscap mobile app.
 * Mirrors frontend/lib/types.ts. Keep in sync with docs/09-api-contract.md.
 */

// Enums
export type MemoryType =
  | "claim"
  | "principle"
  | "definition"
  | "example"
  | "warning"
  | "action"
  | "question"
  | "quote"
  | "reference"
  | "intention";

export type EpistemicLabel =
  | "factual_claim"
  | "opinion"
  | "advice"
  | "anecdote"
  | "prediction"
  | "framework"
  | "personal_reflection"
  | "unresolved"
  | "source_summary";

export type Confidence = "low" | "medium" | "high" | "unknown";
export type SourceStrength = "weak" | "moderate" | "strong" | "unknown";
export type ChatAction =
  | "acknowledge"
  | "conversation"
  | "capture"
  | "answer"
  | "audit"
  | "forget"
  | "reminder"
  | "self"
  | "recent";

// Auth
export interface MobileSessionResponse {
  token: string;
  user_id: string;
  email: string;
  name: string | null;
  image_url: string | null;
  expires_at: string;
}

// Chat
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  action: ChatAction;
  message: string;
  saved: boolean;
  capture: CaptureResponse | null;
  evidence: SearchResult[];
  knowledge_gaps: string[];
  tensions: string[];
  next_step: string | null;
  preference_updates: string[];
  preferences: Record<string, unknown> | null;
}

// Captures
export interface CaptureResponse {
  capture_id: string;
  source_id: string;
  source_title: string | null;
  original_content: string;
  status: string;
  inferred_intents: string[];
  memories: MemoryAtom[];
}

// Memories
export interface MemoryAtom {
  id: string;
  memory_type: MemoryType;
  epistemic_label: EpistemicLabel | null;
  content: string;
  summary: string | null;
  confidence: Confidence;
  confidence_reason: string | null;
  source_strength: SourceStrength;
  embedding_dimensions: number | null;
  relationships: MemoryRelation[];
}

export interface MemoryRelation {
  related_memory_id: string;
  relationship_type: string;
  strength: string;
  explanation: string;
}

export interface RecentMemory {
  memory_id: string;
  source_id: string;
  source_type: string;
  source_title: string | null;
  memory_type: MemoryType;
  epistemic_label: EpistemicLabel | null;
  content: string;
  summary: string | null;
  confidence: Confidence;
  confidence_reason: string | null;
  source_strength: SourceStrength;
  created_at: string;
}

export interface RecentMemoryListResponse {
  count: number;
  limit: number;
  offset: number;
  has_more: boolean;
  memories: RecentMemory[];
}

// Search
export interface SearchResult {
  memory_id: string;
  source_id: string;
  source_title: string | null;
  content: string;
  memory_type: MemoryType;
  epistemic_label: EpistemicLabel | null;
  confidence: Confidence;
  confidence_reason: string | null;
  source_strength: SourceStrength;
  similarity_score: number;
  embedding_dimensions: number | null;
}

export interface SearchResponse {
  query: string;
  min_score: number;
  candidate_count: number;
  embedded_candidate_count: number;
  returned_count: number;
  top_score: number | null;
  results: SearchResult[];
}

// Recalls
export interface RecallMemory {
  memory_id: string;
  source_id: string;
  source_title: string | null;
  memory_type: MemoryType;
  epistemic_label: EpistemicLabel | null;
  content: string;
  summary: string | null;
  confidence: Confidence;
  source_strength: SourceStrength;
  next_review_at: string;
  last_reviewed_at: string | null;
  review_count: number;
  recall_score: number;
  overdue_seconds: number;
  relationships: MemoryRelation[];
}

export interface DueReminder {
  reminder_id: string;
  content: string;
  due_at: string;
  overdue_seconds: number;
  save_as_memory: boolean;
  memory_id: string | null;
  status: string;
}

export interface RecallDueResponse {
  due_count: number;
  now: string;
  memories: RecallMemory[];
  reminders: DueReminder[];
}

export interface RecallAnswerResponse {
  review_id: string;
  memory_id: string;
  feedback: string;
  score: number;
  rating: string;
  understanding_summary: string;
  knowledge_gaps: string[];
  context_to_consider: string[];
  next_question: string | null;
  next_due_at: string;
  review_count: number;
  recall_score: number;
}
