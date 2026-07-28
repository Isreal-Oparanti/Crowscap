import * as SecureStore from "expo-secure-store";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { MobileSessionResponse } from "@/types/api";

const TOKEN_KEY = "crowscap_token";
const SESSION_KEY = "crowscap_session";

export async function saveSession(session: MobileSessionResponse): Promise<void> {
  try {
    await SecureStore.setItemAsync(TOKEN_KEY, session.token);
    await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session));
  } catch {
    await AsyncStorage.setItem(TOKEN_KEY, session.token);
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }
}

export async function getToken(): Promise<string | null> {
  try {
    const val = await SecureStore.getItemAsync(TOKEN_KEY);
    if (val) return val;
  } catch {
    // fallback
  }
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function getSession(): Promise<MobileSessionResponse | null> {
  let raw: string | null = null;
  try {
    raw = await SecureStore.getItemAsync(SESSION_KEY);
  } catch {
    // fallback
  }
  if (!raw) {
    raw = await AsyncStorage.getItem(SESSION_KEY);
  }
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MobileSessionResponse;
  } catch {
    return null;
  }
}

export async function clearSession(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(SESSION_KEY);
  } catch {
    // fallback
  }
  await AsyncStorage.removeItem(TOKEN_KEY);
  await AsyncStorage.removeItem(SESSION_KEY);
}

export function isSessionExpired(session: MobileSessionResponse): boolean {
  return new Date(session.expires_at) <= new Date();
}
