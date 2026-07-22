"use client";

import type { ReactNode } from "react";

type MarkdownTextProps = {
  text: string;
  className?: string;
  compact?: boolean;
  variant?: "assistant" | "compact" | "source";
};

function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; lines: string[] }
  | { type: "quote"; lines: string[] }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "divider" };

const inlinePattern = /(\[[^\]]+\]\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s<]+|`[^`\n]+`|\*\*[^*\n]+?\*\*|__[^_\n]+?__|\*[^*\n]+?\*|_[^_\n]+?_)/g;

export function MarkdownText({
  text,
  className,
  compact = false,
  variant = compact ? "compact" : "assistant",
}: MarkdownTextProps) {
  const blocks = parseBlocks(normalizeDisplayText(text));
  if (blocks.length === 0) return null;

  return (
    <div
      className={cn(
        "min-w-0 break-words [overflow-wrap:anywhere]",
        variant === "assistant" && "text-[13px] font-normal leading-6",
        variant === "compact" && "text-[12px] font-normal leading-5",
        variant === "source" && "text-[12px] font-normal leading-6",
        className,
      )}
    >
      {blocks.map((block, index) => {
        const margin = index === 0 ? "" : variant === "compact" ? "mt-2" : "mt-3";
        if (block.type === "divider") {
          return <div key={index} role="separator" className={cn(margin, "border-t border-border")} />;
        }
        if (block.type === "heading") {
          const Tag = block.level === 1 ? "h2" : block.level === 2 ? "h3" : "h4";
          return (
            <Tag
              key={index}
              className={cn(
                margin,
                "text-balance font-bold leading-snug text-foreground",
                block.level === 1 ? "text-[15px]" : "text-[13px]",
              )}
            >
              {renderInline(block.text)}
            </Tag>
          );
        }
        if (block.type === "quote") {
          return (
            <blockquote key={index} className={cn(margin, "border-l-2 border-border pl-3 text-muted-foreground")}>
              {block.lines.map((line, lineIndex) => (
                <span key={lineIndex}>{lineIndex ? <br /> : null}{renderInline(line)}</span>
              ))}
            </blockquote>
          );
        }
        if (block.type === "list") {
          const Tag = block.ordered ? "ol" : "ul";
          return (
            <Tag key={index} className={cn(margin, "flex flex-col gap-1 pl-5", block.ordered ? "list-decimal" : "list-disc")}>
              {block.items.map((item, itemIndex) => <li key={itemIndex} className="pl-0.5">{renderInline(item)}</li>)}
            </Tag>
          );
        }
        return (
          <p key={index} className={margin}>
            {block.lines.map((line, lineIndex) => (
              <span key={lineIndex}>{lineIndex && !compact ? <br /> : lineIndex ? " " : null}{renderInline(line)}</span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

export function normalizeDisplayText(text: string): string {
  return text
    .replace(/\r\n?/g, "\n")
    .replace(/([.!?])(?=[A-Z][a-z]{2,})/g, "$1 ")
    .replace(/([^\n])(?=(?:What is still missing|Ideas worth comparing|Useful next move|What I know|Why it matters)\s*:)/gi, "$1\n\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function parseBlocks(text: string): Block[] {
  if (!text) return [];
  const blocks: Block[] = [];
  const lines = text.split("\n");
  let paragraph: string[] = [];
  let list: Extract<Block, { type: "list" }> | null = null;
  let quote: string[] = [];
  const flushParagraph = () => { if (paragraph.length) blocks.push({ type: "paragraph", lines: paragraph }); paragraph = []; };
  const flushList = () => { if (list) blocks.push(list); list = null; };
  const flushQuote = () => { if (quote.length) blocks.push({ type: "quote", lines: quote }); quote = []; };
  const flushAll = () => { flushParagraph(); flushList(); flushQuote(); };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushAll(); continue; }
    if (/^(?:---+|\*\*\*+)$/.test(line)) { flushAll(); blocks.push({ type: "divider" }); continue; }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) { flushAll(); blocks.push({ type: "heading", level: heading[1].length, text: heading[2] }); continue; }
    const listMatch = line.match(/^([-*+]\s+|\d+[.)]\s+)(.+)$/);
    if (listMatch) {
      flushParagraph(); flushQuote();
      const ordered = /^\d/.test(listMatch[1]);
      if (!list || list.ordered !== ordered) { flushList(); list = { type: "list", ordered, items: [] }; }
      list.items.push(listMatch[2]);
      continue;
    }
    if (/^>\s?/.test(line)) { flushParagraph(); flushList(); quote.push(line.replace(/^>\s?/, "")); continue; }
    flushList(); flushQuote(); paragraph.push(line);
  }
  flushAll();
  return blocks;
}

function renderInline(text: string): ReactNode[] {
  return text.split(inlinePattern).filter(Boolean).map((part, index) => {
    const markdownLink = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    const bareLink = part.match(/^https?:\/\/[^\s<]+$/);
    if (markdownLink || bareLink) {
      const href = markdownLink?.[2] ?? part.replace(/[),.;!?]+$/, "");
      const label = markdownLink?.[1] ?? readableUrl(href);
      return <a key={index} href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-foreground underline decoration-border underline-offset-4 hover:decoration-foreground">{label}</a>;
    }
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index} className="rounded bg-muted px-1 py-0.5 font-mono text-[0.9em] text-foreground">{part.slice(1, -1)}</code>;
    if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) return <strong key={index} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
    if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) return <em key={index}>{part.slice(1, -1)}</em>;
    return part;
  });
}

function readableUrl(value: string): string {
  try {
    const url = new URL(value);
    const path = decodeURIComponent(url.pathname).replace(/\/$/, "");
    return `${url.hostname.replace(/^www\./, "")}${path.length < 42 ? path : `${path.slice(0, 39)}…`}`;
  } catch { return value.length > 56 ? `${value.slice(0, 53)}…` : value; }
}
