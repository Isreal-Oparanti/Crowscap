import { apiRequest } from "./client";
import type { DueReminder, RecallAnswerResponse, RecallDueResponse } from "@/types/api";

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

export async function completeReminder(reminderId: string): Promise<DueReminder> {
  return apiRequest<DueReminder>(`/recalls/reminders/${reminderId}/complete`, {
    method: "POST",
  });
}

export async function snoozeReminder(reminderId: string, minutes = 60): Promise<DueReminder> {
  return apiRequest<DueReminder>(`/recalls/reminders/${reminderId}/snooze`, {
    method: "POST",
    body: JSON.stringify({ minutes }),
  });
}
