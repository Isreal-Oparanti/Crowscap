import * as SecureStore from "expo-secure-store";
import type { MobileSessionResponse } from "@/types/api";

const TOKEN_KEY = "crowscap_token";
const SESSION_KEY = "crowscap_session";

export async function saveSession(session: MobileSessionResponse): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, session.token);
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session));
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function getSession(): Promise<MobileSessionResponse | null> {
  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MobileSessionResponse;
  } catch {
    return null;
  }
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(SESSION_KEY);
}

export function isSessionExpired(session: MobileSessionResponse): boolean {
  return new Date(session.expires_at) <= new Date();
}
