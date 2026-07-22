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

export function sourceTypeLabel(sourceType: string): string {
  const normalized = sourceType.toLowerCase();
  if (normalized.includes("youtube")) return "YouTube";
  if (normalized.includes("pdf")) return "PDF";
  if (normalized.includes("url") || normalized.includes("article")) return "Article";
  if (normalized.includes("reference")) return "Saved reference";
  return "Note";
}

export function sourceContentLabel(sourceType: string, content: string | null): string {
  if (isReferenceContent(content)) return "Saved reference";
  if (sourceType.toLowerCase().includes("youtube")) return "Transcript";
  return sourceType.toLowerCase().includes("text") ? "Original text" : "Source text";
}

export function humanizeIntent(intent: string): string {
  const labels: Record<string, string> = {
    apply: "For an application",
    watch_later: "Watch later",
    reference: "Reference",
    learn: "Learn",
    remember: "Remember",
    action: "Action item",
  };
  const normalized = intent.trim().toLowerCase();
  return labels[normalized] ?? normalized.replace(/[_-]+/g, " ").replace(/^./, (value) => value.toUpperCase());
}

export type ReferenceFields = {
  link?: string;
  title?: string;
  description?: string;
  reason?: string;
};

export function parseReferenceContent(content: string | null): ReferenceFields | null {
  if (!content || !isReferenceContent(content)) return null;
  const fields: ReferenceFields = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    const match = line.match(/^(Reference link|Known title|Known description|Why it matters):\s*(.*)$/i);
    if (!match) continue;
    const key = match[1].toLowerCase();
    if (key === "reference link") fields.link = match[2];
    else if (key === "known title") fields.title = match[2];
    else if (key === "known description") fields.description = match[2];
    else fields.reason = match[2];
  }
  return fields;
}

export function formatTranscriptForDisplay(content: string): string {
  const cleaned = content
    .replace(/^WEBVTT[^\n]*\n?/i, "")
    .replace(/^\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s+-->.*$/gm, "")
    .replace(/^\[?(?:music|applause|laughter)\]?$/gim, "")
    .replace(/<\/?c[^>]*>|<\d{2}:\d{2}:\d{2}[^>]*>/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  const lines = cleaned.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 4) return cleaned;
  const paragraphs: string[] = [];
  for (let index = 0; index < lines.length; index += 4) paragraphs.push(lines.slice(index, index + 4).join(" "));
  return paragraphs.join("\n\n");
}

function isReferenceContent(content: string | null): boolean {
  return Boolean(content && /^Reference link:/im.test(content));
}
