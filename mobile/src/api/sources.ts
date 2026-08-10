import { apiRequest } from "./client";

export type SourceContentResponse = {
  source_id: string;
  source_type: string;
  title: string | null;
  original_url: string | null;
  original_content: string | null;
};

export async function getSourceContent(sourceId: string): Promise<SourceContentResponse> {
  return apiRequest<SourceContentResponse>(`/sources/${sourceId}`);
}
