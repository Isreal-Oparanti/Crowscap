import { apiRequest } from "./client";
import type { CaptureResponse } from "@/types/api";

export async function captureText(payload: {
  content: string;
  intent_text?: string;
  user_note?: string;
  source_title?: string;
}): Promise<CaptureResponse> {
  return apiRequest<CaptureResponse>("/captures/text", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
