"use client";

import type { ReactNode } from "react";

type MarkdownTextProps = {
  text: string;
  className?: string;
  compact?: boolean;
};

const inlinePattern =
  /(\[[^\]]+\]\(https?:\/\/[^\s)]+\)|`[^`]+`|\*\*[^*\n]+?\*\*|\*[^*\n]+?\*)/g;

export function MarkdownText({
  text,
  className,
  compact = false,
}: MarkdownTextProps) {
  const blocks = text.trim().split(/\n{2,}/).filter(Boolean);

  if (blocks.length === 0) return null;

  return (
    <div className={className}>
      {blocks.map((block, index) => {
        const lines = block
          .split(/\n/)
          .map((line) => line.trim())
          .filter(Boolean);
        const unordered = lines.every((line) => /^[-*]\s+/.test(line));
        const ordered = lines.every((line) => /^\d+[.)]\s+/.test(line));
        const spacing = index > 0 ? "mt-2" : "";

        if (unordered) {
          return (
            <ul
              key={`${block}-${index}`}
              className={`${spacing} list-disc space-y-1 pl-5`}
            >
              {lines.map((line) => (
                <li key={line}>{renderInline(line.replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }

        if (ordered) {
          return (
            <ol
              key={`${block}-${index}`}
              className={`${spacing} list-decimal space-y-1 pl-5`}
            >
              {lines.map((line) => (
                <li key={line}>
                  {renderInline(line.replace(/^\d+[.)]\s+/, ""))}
                </li>
              ))}
            </ol>
          );
        }

        return (
          <p key={`${block}-${index}`} className={spacing}>
            {renderInline(lines.join(compact ? " " : "\n"))}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(text: string): ReactNode[] {
  const parts = text.split(inlinePattern).filter((part) => part.length > 0);

  return parts.map((part, index) => {
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (link) {
      return (
        <a
          key={`${part}-${index}`}
          href={link[2]}
          target="_blank"
          rel="noreferrer"
          className="font-bold underline decoration-[#b7c8bf] underline-offset-4 transition hover:text-[#111111]"
        >
          {link[1]}
        </a>
      );
    }

    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={`${part}-${index}`}
          className="rounded bg-[#f1f2f3] px-1 py-0.5 text-[0.92em] font-bold"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }

    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={`${part}-${index}`}>{part.slice(1, -1)}</em>;
    }

    return part;
  });
}
