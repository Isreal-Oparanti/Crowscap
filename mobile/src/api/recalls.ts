import { apiRequest } from "./client";
import type { DueReminder, RecallAnswerResponse, RecallDueResponse, RecallQuickAction } from "@/types/api";

export async function getDueRecalls(limit = 50, targetMemoryId?: string): Promise<RecallDueResponse> {
  let url = `/recalls/due?limit=${limit}`;
  if (targetMemoryId) {
    url += `&target_memory_id=${encodeURIComponent(targetMemoryId)}`;
  }
  return apiRequest<RecallDueResponse>(url);
}

export async function submitQuickRecall(
  memoryId: string,
  action: RecallQuickAction
): Promise<RecallAnswerResponse> {
  return apiRequest<RecallAnswerResponse>(`/recalls/${memoryId}/quick`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
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
