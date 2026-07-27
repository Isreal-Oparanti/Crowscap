import { apiRequest } from "./client";
import type { RecallDueResponse, RecallAnswerResponse } from "@/types/api";

export async function getDueRecalls(limit = 50): Promise<RecallDueResponse> {
  return apiRequest<RecallDueResponse>(`/recalls/due?limit=${limit}`);
}

export async function answerRecall(
  recallId: string,
  payload: { answer: string; self_rating?: number }
): Promise<RecallAnswerResponse> {
  return apiRequest<RecallAnswerResponse>(`/recalls/${recallId}/answer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
