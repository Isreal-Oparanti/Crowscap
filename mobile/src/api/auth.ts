import { apiRequest } from "./client";
import type { MobileSessionResponse, EmailCodeStartResponse } from "@/types/api";

export async function createMobileSession(payload: {
  id_token: string;
  platform: "ios" | "android";
}): Promise<MobileSessionResponse> {
  return apiRequest<MobileSessionResponse>("/auth/mobile-session", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startEmailSession(payload: {
  email: string;
  mode: "signup" | "login";
}): Promise<EmailCodeStartResponse> {
  return apiRequest<EmailCodeStartResponse>("/auth/email/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export async function verifyEmailSession(payload: {
  email: string;
  code: string;
  mode: "signup" | "login";
}): Promise<MobileSessionResponse> {
  return apiRequest<MobileSessionResponse>("/auth/email/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
