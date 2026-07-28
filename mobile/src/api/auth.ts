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

export async function createDemoSession(payload: {
  platform: "ios" | "android";
}): Promise<MobileSessionResponse> {
  void payload;
  const expiresAt = new Date();
  expiresAt.setDate(expiresAt.getDate() + 30);

  return {
    token: "crowscap-demo-workspace",
    user_id: "demo_yc_user",
    email: "yc@crowscap.xyz",
    name: "YC Reviewer",
    image_url: null,
    expires_at: expiresAt.toISOString(),
  };
}
