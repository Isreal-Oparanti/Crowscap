import {
  ArrowUpRight,
  CircleAlert,
  GitCompareArrows,
  Lightbulb,
  Quote,
  Sparkles,
} from "lucide-react";
import { humanizeRelationshipText } from "@/lib/chat";
import type { MemoryCard, SearchResult } from "@/lib/types";

type DisplayMemory = MemoryCard | SearchResult;

export function MemoryCardView({
  memory,
  compact = false,
}: {
  memory: DisplayMemory;
  compact?: boolean;
}) {
  const memoryId = "id" in memory ? memory.id : memory.memory_id;
  const sourceTitle = "source_title" in memory ? memory.source_title : null;
  const sourceType = "source_type" in memory ? memory.source_type : "text";
  const relationships =
    "relationships" in memory ? memory.relationships : undefined;
  const score = "similarity_score" in memory ? memory.similarity_score : null;

  return (
    <article
      data-memory-id={memoryId}
      className="group rounded-lg border border-[#dfe2e3] bg-white p-4 shadow-[0_8px_30px_rgba(17,17,17,0.035)] transition hover:border-[#c9cdcf]"
    >
      <div className="flex items-start gap-3">
        <MemoryIcon type={memory.memory_type} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-extrabold uppercase text-[#6f7376]">
              {memory.memory_type}
            </span>
            <span className="size-0.5 rounded-full bg-[#b4b7b9]" />
            <span className="text-[10px] font-semibold text-[#85888b]">
              {memory.confidence} confidence
            </span>
            <span className="rounded bg-[#f1f2f3] px-1.5 py-0.5 text-[9px] font-extrabold uppercase text-[#727679]">
              {sourceType}
            </span>
            {score !== null ? (
              <span className="ml-auto text-[10px] font-bold text-[#2d7058]">
                {Math.round(score * 100)}% match
              </span>
            ) : null}
          </div>
          <p
            className={`mt-2 font-semibold leading-relaxed text-[#1d1e1f] ${
              compact ? "text-[13px]" : "text-[14px]"
            }`}
          >
            {memory.content}
          </p>
          {sourceTitle ? (
            <div className="mt-3 flex items-center gap-1.5 text-[10px] font-medium text-[#7d8083]">
              <Quote size={12} />
              <span className="truncate">{sourceTitle}</span>
              <ArrowUpRight size={11} />
            </div>
          ) : null}
        </div>
      </div>

      {relationships && relationships.length > 0 ? (
        <div className="mt-3 border-t border-[#eceeef] pt-3">
          <div className="flex items-start gap-2 text-[#8b5a1e]">
            <GitCompareArrows className="mt-0.5 shrink-0" size={13} />
            <div>
              <p className="text-[9px] font-extrabold uppercase">
                {relationshipLabel(relationships[0].relationship_type)}
              </p>
              {relationships[0].explanation ? (
                <p className="mt-1 text-[10px] font-semibold leading-relaxed">
                  {humanizeRelationshipText(relationships[0].explanation)}
                </p>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </article>
  );
}

function relationshipLabel(type: string) {
  const labels: Record<string, string> = {
    confirms: "Agrees with something you saved",
    conflicts: "Disagrees with something you saved",
    tension: "Worth comparing with something you saved",
    extends: "Adds to something you saved",
    qualifies: "Adds an important condition",
  };
  return labels[type] ?? "Connected to something you saved";
}

function MemoryIcon({ type }: { type: string }) {
  const Icon =
    type === "warning"
      ? CircleAlert
      : type === "action"
        ? Sparkles
        : Lightbulb;
  const colors =
    type === "warning"
      ? "bg-[#f8ebec] text-[#9b4c51]"
      : type === "action"
        ? "bg-[#eaf4ef] text-[#2d7058]"
        : "bg-[#eaf2f7] text-[#356b8f]";

  return (
    <div
      className={`flex size-8 shrink-0 items-center justify-center rounded-md ${colors}`}
    >
      <Icon size={15} strokeWidth={2} />
    </div>
  );
}
