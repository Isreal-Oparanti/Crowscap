import { apiRequest } from "./client";
import type { ChatRequest, ChatResponse } from "@/types/api";

export async function sendChatMessage(
  payload: ChatRequest
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
