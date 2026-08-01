import { apiRequest } from "./client";
import type { RecentMemoryListResponse } from "@/types/api";

export async function getRecentMemories(
  limit = 20,
  offset = 0
): Promise<RecentMemoryListResponse> {
  return apiRequest<RecentMemoryListResponse>(
    `/memories/recent?limit=${limit}&offset=${offset}`
  );
}

export async function archiveMemory(memoryId: string): Promise<void> {
  await apiRequest(`/memories/${memoryId}/archive`, {
    method: "POST",
    body: JSON.stringify({ reason: "user_dismissed" }),
  });
}

export async function deleteMemory(memoryId: string): Promise<void> {
  await apiRequest(`/memories/${memoryId}`, { method: "DELETE" });
}
