import Constants from "expo-constants";

export const backendUrl =
  Constants.expoConfig?.extra?.backendUrl ??
  process.env.EXPO_PUBLIC_BACKEND_URL ??
  "https://api.crowscap.xyz";

import { getToken } from "@/auth/session";

/** Retrieve the stored auth token. Injected by session.ts at runtime. */
let _getToken: (() => Promise<string | null>) | null = getToken;

export async function getAuthToken(): Promise<string | null> {
  return _getToken ? await _getToken() : null;
}

export function setTokenProvider(fn: () => Promise<string | null>) {
  _getToken = fn;
}


/**
 * Base API client for the Crowscap mobile app.
 * Attaches Authorization: Bearer <token> to every request.
 * Throws an ApiError on non-2xx responses.
 */
export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = _getToken ? await _getToken() : null;
  const isMultipart = typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isMultipart ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${backendUrl}/api/v1${path}`, {
    ...options,
    headers,
  });

  const responseText = await response.text();

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = responseText ? JSON.parse(responseText) : null;
      detail = body?.detail ?? detail;
    } catch {
      // Non-JSON error body: keep status string.
    }
    throw new ApiError(response.status, detail);
  }

  if (!responseText) {
    return undefined as T;
  }

  return JSON.parse(responseText) as T;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}
