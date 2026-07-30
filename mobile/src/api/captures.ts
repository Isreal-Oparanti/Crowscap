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

export async function capturePdf(payload: {
  uri: string;
  name: string;
  mimeType?: string | null;
  intent_text?: string;
  user_note?: string;
}): Promise<CaptureResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: payload.uri,
    name: payload.name,
    type: payload.mimeType || "application/pdf",
  } as unknown as Blob);

  if (payload.intent_text) {
    formData.append("intent_text", payload.intent_text);
  }
  if (payload.user_note) {
    formData.append("user_note", payload.user_note);
  }

  return apiRequest<CaptureResponse>("/captures/pdf", {
    method: "POST",
    body: formData,
  });
}
