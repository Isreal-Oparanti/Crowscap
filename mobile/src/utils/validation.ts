import { LIMITS } from "@/constants/limits";

export function validateChatMessage(text: string): string | null {
  if (!text.trim()) return "Message cannot be empty.";
  if (text.length > LIMITS.CHAT_MESSAGE_MAX) return "Message is too long.";
  return null;
}

export function validateSearchQuery(text: string): string | null {
  if (text.trim().length < LIMITS.SEARCH_QUERY_MIN) return "Query is too short.";
  if (text.length > LIMITS.SEARCH_QUERY_MAX) return "Query is too long.";
  return null;
}

export function validateCaptureText(text: string): string | null {
  if (text.trim().length < LIMITS.CAPTURE_TEXT_MIN) return "Too short to capture.";
  if (text.length > LIMITS.CAPTURE_TEXT_MAX) return "Content is too long.";
  return null;
}
