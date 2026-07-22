import type {
  CaptureResponse,
  BeliefAuditResponse,
  ChatResponse,
  ConversationResponse,
  ConversationTurn,
  DueRecallsResponse,
  PerspectiveNoteListResponse,
  ReminderResponse,
  RecallAnswerResponse,
  RecallQuickAction,
  RecallQuickResponse,
  SearchResponse,
  SourceContentResponse,
  UserPreferenceLearningResponse,
  UserPreferenceProfile,
} from "@/lib/types";

function errorMessageFromPayload(payload: unknown): string {
  if (typeof payload === "object" && payload !== null) {
    if ("detail" in payload && typeof payload.detail === "string") {
      return payload.detail;
    }
    // FastAPI validation errors return `detail` as an array of error objects.
    // Surface the first human-readable message instead of a generic failure.
    if ("detail" in payload && Array.isArray(payload.detail)) {
      const first = payload.detail[0];
      if (
        typeof first === "object" &&
        first !== null &&
        "msg" in first &&
        typeof first.msg === "string"
      ) {
        return `Crowscap could not accept that input: ${first.msg}`;
      }
    }
    if ("error" in payload && typeof payload.error === "string") {
      return payload.error;
    }
    if ("message" in payload && typeof payload.message === "string") {
      return payload.message;
    }
  }
  return "Crowscap could not complete that request.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  let response: Response;
  try {
    response = await fetch(`/api/backend/${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body && !isFormData ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new Error(
      "Crowscap could not reach the memory service. Please check your internet connection and try again.",
    );
  }

  const rawPayload = await response.text();
  let payload: unknown = null;
  if (rawPayload) {
    try {
      payload = JSON.parse(rawPayload);
    } catch {
      payload = {
        detail:
          rawPayload.trim() || "Crowscap returned an unreadable response.",
      };
    }
  }
  if (!response.ok) {
    throw new Error(errorMessageFromPayload(payload));
  }
  return payload as T;
}

export function captureText(content: string): Promise<CaptureResponse> {
  return request<CaptureResponse>("captures/text", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

// Keep in sync with backend ConversationTurn/ChatRequest limits.
const MAX_HISTORY_TURN_CHARS = 4000;
const MAX_HISTORY_TURNS = 12;

export function sendChatMessage(
  message: string,
  history: ConversationTurn[],
  conversationId?: string | null,
): Promise<ChatResponse> {
  // History is context, not payload. Clamp every turn so one long paste can
  // never make subsequent requests in the conversation fail validation.
  const safeHistory = history
    .filter((turn) => turn.content.trim().length > 0)
    .slice(-MAX_HISTORY_TURNS)
    .map((turn) => ({
      role: turn.role,
      content: turn.content.slice(0, MAX_HISTORY_TURN_CHARS),
    }));

  return request<ChatResponse>("chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      history: safeHistory,
    }),
  });
}

export function uploadPdfToChat(
  file: File,
  userMessage?: string,
  conversationId?: string | null,
): Promise<ChatResponse> {
  const body = new FormData();
  body.append("file", file);
  body.append(
    "intent_text",
    userMessage
      ? userMessage
      : "Extract the important ideas from this PDF and keep them in my memory.",
  );
  body.append(
    "user_note",
    userMessage
      ? `User message with PDF: ${userMessage}`
      : "Uploaded from the Crowscap chat composer as a PDF source.",
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

export function learnPreferencesNow(): Promise<UserPreferenceLearningResponse> {
  return request<UserPreferenceLearningResponse>("preferences/learn-now", {
    method: "POST",
  });
}

export function getDuePerspectiveNotes(
  includeFuture = false,
  limit = 10,
): Promise<PerspectiveNoteListResponse> {
  return request<PerspectiveNoteListResponse>(
    `memories/perspective-notes/due?limit=${limit}&include_future=${includeFuture}`,
  );
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
