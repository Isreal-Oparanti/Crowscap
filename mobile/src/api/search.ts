import { apiRequest } from "./client";
import type { SearchResponse } from "@/types/api";

export async function searchMemories(payload: {
  query: string;
  limit?: number;
  include_archived?: boolean;
}): Promise<SearchResponse> {
  return apiRequest<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify({ limit: 10, include_archived: false, ...payload }),
  });
}
