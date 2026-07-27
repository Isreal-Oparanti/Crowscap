import { apiRequest } from "./client";
import type { MobileSessionResponse } from "@/types/api";

export async function createMobileSession(payload: {
  id_token: string;
  platform: "ios" | "android";
}): Promise<MobileSessionResponse> {
  return apiRequest<MobileSessionResponse>("/auth/mobile-session", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
