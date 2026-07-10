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

export function humanizeRelationshipText(text: string): string {
  return text
    .replace(/\bcontext-dependent tension\b/gi, "context-dependent difference")
    .replace(/\btensions\b/gi, "differences")
    .replace(/\btension\b/gi, "difference");
}
