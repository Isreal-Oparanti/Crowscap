import type {
  CaptureResponse,
  BeliefAuditResponse,
  ChatResponse,
  ConversationResponse,
  ConversationTurn,
  DueRecallsResponse,
  ReminderResponse,
  RecallAnswerResponse,
  RecallQuickAction,
  RecallQuickResponse,
  SearchResponse,
  SourceContentResponse,
  UserPreferenceProfile,
} from "@/lib/types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body && !isFormData ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  const payload: unknown = await response.json();
  if (!response.ok) {
    const detail =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : "Crowscap could not complete that request.";
    throw new Error(detail);
  }
  return payload as T;
}

export function captureText(content: string): Promise<CaptureResponse> {
  return request<CaptureResponse>("captures/text", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function sendChatMessage(
  message: string,
  history: ConversationTurn[],
  conversationId?: string | null,
): Promise<ChatResponse> {
  return request<ChatResponse>("chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      history: history.slice(-12),
    }),
  });
}

export function uploadPdfToChat(
  file: File,
  conversationId?: string | null,
): Promise<ChatResponse> {
  const body = new FormData();
  body.append("file", file);
  body.append(
    "intent_text",
    "Extract the important ideas from this PDF and keep them in my memory.",
  );
  body.append(
    "user_note",
    "Uploaded from the Crowscap chat composer as a PDF source.",
  );
  if (conversationId) {
    body.append("conversation_id", conversationId);
  }

  return request<ChatResponse>("chat/pdf", {
    method: "POST",
    body,
  });
}

export function getCurrentConversation(): Promise<ConversationResponse | null> {
  return request<ConversationResponse | null>("chat/conversations/current");
}

export function getPreferences(): Promise<UserPreferenceProfile> {
  return request<UserPreferenceProfile>("preferences/me");
}

export function searchMemories(query: string): Promise<SearchResponse> {
  return request<SearchResponse>("search", {
    method: "POST",
    body: JSON.stringify({
      query,
      limit: 10,
      min_score: 0.25,
      include_archived: false,
    }),
  });
}

export function auditBelief(topic: string): Promise<BeliefAuditResponse> {
  return request<BeliefAuditResponse>("beliefs/audit", {
    method: "POST",
    body: JSON.stringify({
      topic,
      include_public_evidence: true,
      public_query_count: 3,
      public_results_per_query: 3,
    }),
  });
}

export function getDueRecalls(limit = 12): Promise<DueRecallsResponse> {
  return request<DueRecallsResponse>(`recalls/due?limit=${limit}`);
}

export function completeReminder(reminderId: string): Promise<ReminderResponse> {
  return request<ReminderResponse>(`recalls/reminders/${reminderId}/complete`, {
    method: "POST",
  });
}

export function snoozeReminder(
  reminderId: string,
  minutes = 60,
): Promise<ReminderResponse> {
  return request<ReminderResponse>(`recalls/reminders/${reminderId}/snooze`, {
    method: "POST",
    body: JSON.stringify({ minutes }),
  });
}

export function getSourceContent(
  sourceId: string,
): Promise<SourceContentResponse> {
  return request<SourceContentResponse>(`sources/${sourceId}`);
}

export function submitRecallAnswer(
  memoryId: string,
  answer: string,
  selfRating?: number,
): Promise<RecallAnswerResponse> {
  return request<RecallAnswerResponse>(`recalls/${memoryId}/answer`, {
    method: "POST",
    body: JSON.stringify({
      answer,
      self_rating: selfRating,
    }),
  });
}

export function submitQuickRecall(
  memoryId: string,
  action: RecallQuickAction,
): Promise<RecallQuickResponse> {
  return request<RecallQuickResponse>(`recalls/${memoryId}/quick`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}
