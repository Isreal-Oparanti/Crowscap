export function formatRelativeOverdue(seconds: number): string {
  if (seconds < 3600) {
    const minutes = Math.max(1, Math.round(seconds / 60));
    return `${minutes}m overdue`;
  }
  if (seconds < 86400) {
    return `${Math.round(seconds / 3600)}h overdue`;
  }
  return `${Math.round(seconds / 86400)}d overdue`;
}

export function formatFriendlyDateTime(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "scheduled time";

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDelta = Math.round(
    (startOfDate.getTime() - startOfToday.getTime()) / 86_400_000,
  );
  const time = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);

  if (dayDelta === 0) return `today at ${time}`;
  if (dayDelta === 1) return `tomorrow at ${time}`;
  if (dayDelta === -1) return `yesterday at ${time}`;

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: date.getFullYear() === now.getFullYear() ? undefined : "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function humanizeRelationshipText(text: string): string {
  return text
    .replace(/\bcontext-dependent tension\b/gi, "context-dependent difference")
    .replace(/\btensions\b/gi, "differences")
    .replace(/\btension\b/gi, "difference");
}
