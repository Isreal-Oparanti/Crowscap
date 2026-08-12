import { apiRequest } from "./client";
import type { ChatRequest, ChatResponse, ConversationResponse } from "@/types/api";

export async function sendChatMessage(
  payload: ChatRequest
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCurrentConversation(): Promise<ConversationResponse | null> {
  return apiRequest<ConversationResponse | null>("/chat/conversations/current");
}

export type PaginatedMessagesResponse = {
  messages: Array<{
    id: string;
    conversation_id: string;
    role: "user" | "assistant";
    content: string;
    action?: string;
    metadata_json?: Record<string, unknown>;
    created_at: string;
  }>;
  has_more: boolean;
};

export async function getChatMessages(
  limit = 20,
  beforeId?: string
): Promise<PaginatedMessagesResponse> {
  const query = beforeId
    ? `/chat/messages?limit=${limit}&before_id=${beforeId}`
    : `/chat/messages?limit=${limit}`;
  return apiRequest<PaginatedMessagesResponse>(query);
}

export async function listConversations(
  limit = 50
): Promise<ConversationResponse[]> {
  return apiRequest<ConversationResponse[]>(`/chat/conversations?limit=${limit}`);
}

export async function createConversation(): Promise<ConversationResponse> {
  return apiRequest<ConversationResponse>("/chat/conversations", {
    method: "POST",
  });
}

export async function getConversation(
  conversationId: string
): Promise<ConversationResponse> {
  return apiRequest<ConversationResponse>(`/chat/conversations/${conversationId}`);
}

export async function deleteConversation(
  conversationId: string
): Promise<void> {
  return apiRequest<void>(`/chat/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

export async function learnPreferencesNow(): Promise<{ updates: string[] }> {
  return apiRequest<{ updates: string[] }>("/preferences/learn-now", {
    method: "POST",
  });
}

