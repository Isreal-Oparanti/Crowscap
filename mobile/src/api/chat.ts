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

