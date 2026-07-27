import type { MemoryType } from "@/types/api";

/** Format a date string as "Jul 25" */
export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recent";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Truncate text to a max character count */
export function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "…";
}

/** Convert a memory type to a human-readable display label */
export function memoryTypeLabel(type: MemoryType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

/** Convert a confidence value to a display string */
export function confidenceLabel(value: string): string {
  const map: Record<string, string> = {
    high: "High confidence",
    medium: "Medium confidence",
    low: "Low confidence",
    unknown: "Unrated",
  };
  return map[value] ?? value;
}

/** Format overdue seconds as a readable string */
export function formatOverdue(seconds: number): string {
  if (seconds < 3600) return `${Math.round(seconds / 60)}m overdue`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h overdue`;
  return `${Math.round(seconds / 86400)}d overdue`;
}
