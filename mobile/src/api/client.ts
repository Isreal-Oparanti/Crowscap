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


export function formatFriendlyError(detail: string, status?: number): string {
  const raw = (detail || "").trim();

  if (status === 404 || status === 500 || status === 502 || status === 503 || status === 504) {
    return "Network Disconnect. Please try again.";
  }

  if (
    /^(HTTP\s*\d+|Network request failed|Failed to fetch|TypeError|NetworkError)/i.test(raw) ||
    raw.includes("HTTP 404") ||
    raw.includes("HTTP 502") ||
    raw.includes("HTTP 503") ||
    raw.includes("HTTP 500") ||
    raw.includes("[object Object]") ||
    raw.toLowerCase().includes("not found")
  ) {
    return "Network Disconnect. Please try again.";
  }

  return raw || "Network Disconnect. Please try again.";
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

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1${path}`, {
      ...options,
      headers,
    });
  } catch (netErr) {
    throw new ApiError(0, "Network Disconnect. Please try again.");
  }

  const responseText = await response.text();

  if (!response.ok) {
    let detail = "Network Disconnect. Please try again.";
    try {
      const body = responseText ? JSON.parse(responseText) : null;
      if (body) {
        if (typeof body.detail === "string") {
          detail = body.detail;
        } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
          detail = String(body.detail[0].msg);
        } else if (typeof body.detail === "object" && body.detail !== null) {
          detail = String(body.detail.message || JSON.stringify(body.detail));
        } else if (body.message && typeof body.message === "string") {
          detail = body.message;
        }
      }
    } catch {
      // Non-JSON error body
    }
    throw new ApiError(response.status, formatFriendlyError(detail, response.status));
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
