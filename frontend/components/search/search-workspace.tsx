"use client";

import {
  Archive,
  ArrowRight,
  BrainCircuit,
  Clock3,
  FileText,
  Search,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { MemoryCardView } from "@/components/memory/memory-card";
import { AppShell } from "@/components/shell/app-shell";
import { MarkdownText } from "@/components/ui/markdown-text";
import type { AppShellUser } from "@/components/shell/app-shell";
import {
  archiveMemory,
  getDueRecalls,
  getRecentMemories,
  searchMemories,
} from "@/lib/api";
import type { RecentMemory, SearchResponse } from "@/lib/types";

export function SearchWorkspace({ user }: { user: AppShellUser }) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dueCount, setDueCount] = useState(0);
  const [recent, setRecent] = useState<RecentMemory[]>([]);
  const [recentOffset, setRecentOffset] = useState(0);
  const [recentHasMore, setRecentHasMore] = useState(false);
  const [recentLoading, setRecentLoading] = useState(true);
  const [archivingId, setArchivingId] = useState<string | null>(null);

  useEffect(() => {
    getDueRecalls(1)
      .then((response) => setDueCount(response.due_count))
      .catch(() => setDueCount(0));
  }, []);

  useEffect(() => {
    loadRecent(0);
  }, []);

  async function loadRecent(offset: number) {
    setRecentLoading(true);
    setError(null);
    try {
      const response = await getRecentMemories(16, offset);
      setRecent((current) =>
        offset === 0 ? response.memories : [...current, ...response.memories],
      );
      setRecentOffset(offset + response.memories.length);
      setRecentHasMore(response.has_more);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Recent memories are unavailable.",
      );
    } finally {
      setRecentLoading(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length < 2 || loading) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await searchMemories(query.trim()));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Search is unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function archiveRecent(memoryId: string) {
    if (archivingId) return;
    setArchivingId(memoryId);
    setError(null);
    try {
      await archiveMemory(memoryId);
      setRecent((current) =>
        current.filter((memory) => memory.memory_id !== memoryId),
      );
      setResult((current) =>
        current
          ? {
              ...current,
              returned_count: Math.max(0, current.returned_count - 1),
              results: current.results.filter(
                (memory) => memory.memory_id !== memoryId,
              ),
            }
          : current,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "That memory could not be removed.",
      );
    } finally {
      setArchivingId(null);
    }
  }

  return (
    <AppShell
      dueCount={dueCount}
      title="Search memory"
      subtitle="Find meaning, not just matching words"
      user={user}
      context={
        <SearchContext
          query={result?.query ?? null}
          count={result?.returned_count ?? 0}
          topScore={result?.top_score ?? null}
        />
      }
    >
      <div className="conversation-scroll flex-1 overflow-y-auto px-4 pb-28 pt-7 md:px-8 md:pb-10 md:pt-10">
        <div className="mx-auto max-w-[780px]">
          <div className="max-w-[620px]">
            <p className="text-[10px] font-extrabold uppercase text-[#7e8285]">
              Your memory
            </p>
            <h2 className="mt-2 text-[27px] font-[760] leading-tight md:text-[32px]">
              What are you trying to reach?
            </h2>
          </div>

          <form onSubmit={submit} className="relative mt-7">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#696d70]"
              size={19}
            />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try “what did I learn about distribution?”"
              className="h-14 w-full rounded-lg border border-[#cfd2d4] bg-white pl-12 pr-24 text-[13px] font-semibold outline-none transition focus:border-[#858a8d] focus:shadow-[0_10px_34px_rgba(17,17,17,0.06)]"
            />
            {query ? (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setResult(null);
                }}
                aria-label="Clear search"
                className="absolute right-12 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center text-[#777b7e]"
              >
                <X size={16} />
              </button>
            ) : null}
            <button
              type="submit"
              aria-label="Search memories"
              disabled={query.trim().length < 2 || loading}
              className="absolute right-2 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-md bg-[#111111] text-white disabled:bg-[#d1d3d4] [&_svg]:stroke-white"
            >
              <ArrowRight size={17} />
            </button>
          </form>

          {loading ? (
            <div className="mt-12 flex items-center gap-3 text-[#6f7376]">
              <BrainCircuit size={16} />
              <span className="text-[12px] font-semibold">
                Reaching across your memory
              </span>
            </div>
          ) : null}

          {error ? (
            <p className="mt-8 text-[12px] font-semibold text-[#9b4c51]">
              {error}
            </p>
          ) : null}

          {result ? (
            <div className="mt-9 rise-in">
              <div className="mb-4 flex items-end justify-between">
                <div>
                  <p className="text-[11px] font-extrabold">
                    {result.returned_count > 0
                      ? `${result.returned_count} connected memories`
                      : "No strong connection yet"}
                  </p>
                  <p className="mt-1 text-[10px] text-[#85888b]">
                    Ranked by meaning across {result.embedded_candidate_count}{" "}
                    searchable memories
                  </p>
                </div>
                {result.top_score !== null ? (
                  <span className="text-[10px] font-bold text-[#2d7058]">
                    {Math.round(result.top_score * 100)}% closest
                  </span>
                ) : null}
              </div>

              <div className="grid gap-3">
                {result.results.map((memory) => (
                  <MemoryCardView key={memory.memory_id} memory={memory} />
                ))}
              </div>
            </div>
          ) : null}

          {!result ? <SearchSuggestions onPick={setQuery} /> : null}

          <RecentMemories
            memories={recent}
            loading={recentLoading}
            hasMore={recentHasMore}
            archivingId={archivingId}
            onArchive={archiveRecent}
            onLoadMore={() => loadRecent(recentOffset)}
          />
        </div>
      </div>
    </AppShell>
  );
}

function SearchSuggestions({ onPick }: { onPick: (query: string) => void }) {
  return (
    <div className="mt-10 grid gap-2 sm:grid-cols-2">
      {[
        "What do I know about distribution?",
        "Find ideas I saved about product design",
        "Where have my sources disagreed?",
        "What have I learned but not applied?",
      ].map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          onClick={() => onPick(suggestion)}
          className="min-h-16 rounded-lg border border-[#e0e2e3] bg-[#fafafa] px-4 py-3 text-left text-[11px] font-semibold leading-relaxed transition hover:border-[#c8ccce] hover:bg-white"
        >
          {suggestion}
        </button>
      ))}
    </div>
  );
}

function RecentMemories({
  memories,
  loading,
  hasMore,
  archivingId,
  onArchive,
  onLoadMore,
}: {
  memories: RecentMemory[];
  loading: boolean;
  hasMore: boolean;
  archivingId: string | null;
  onArchive: (memoryId: string) => void;
  onLoadMore: () => void;
}) {
  return (
    <section className="mt-10 border-t border-[#e6e8e9] pt-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-extrabold uppercase text-[#7e8285]">
            Recently saved
          </p>
          <h3 className="mt-1 text-[18px] font-[750] leading-tight">
            Your newest memories
          </h3>
        </div>
        {loading ? (
          <span className="text-[10px] font-bold text-[#85888b]">
            Loading
          </span>
        ) : null}
      </div>

      {!loading && memories.length === 0 ? (
        <p className="mt-4 rounded-lg border border-[#e3e5e6] bg-[#fafafa] px-4 py-5 text-[12px] font-semibold leading-relaxed text-[#777b7e]">
          No active memories yet. Save an idea, link, PDF, or video and it will
          appear here.
        </p>
      ) : null}

      <div className="mt-4 divide-y divide-[#eceeef] overflow-hidden rounded-lg border border-[#e1e3e4] bg-white">
        {memories.map((memory) => (
          <RecentMemoryRow
            key={memory.memory_id}
            memory={memory}
            archiving={archivingId === memory.memory_id}
            onArchive={() => onArchive(memory.memory_id)}
          />
        ))}
      </div>

      {hasMore ? (
        <button
          type="button"
          disabled={loading}
          onClick={onLoadMore}
          className="mt-4 rounded-md border border-[#d7dadc] bg-white px-3 py-2 text-[11px] font-extrabold text-[#4d5255] transition hover:border-[#9fa4a7] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Load more
        </button>
      ) : null}
    </section>
  );
}

function RecentMemoryRow({
  memory,
  archiving,
  onArchive,
}: {
  memory: RecentMemory;
  archiving: boolean;
  onArchive: () => void;
}) {
  return (
    <article className="group flex items-start gap-3 px-4 py-4 transition hover:bg-[#fbfcfc]">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-[#eef4f7] text-[#356b8f]">
        <FileText size={15} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[9px] font-extrabold uppercase text-[#6f7376]">
            {memory.memory_type}
          </span>
          <span className="size-0.5 rounded-full bg-[#b8bbbd]" />
          <span className="text-[9px] font-bold uppercase text-[#85888b]">
            {memory.source_type}
          </span>
          <span className="ml-auto flex items-center gap-1 text-[9px] font-semibold text-[#85888b]">
            <Clock3 size={11} />
            {formatRecentDate(memory.created_at)}
          </span>
        </div>
        <MarkdownText
          text={memory.summary ?? memory.content}
          className="mt-1 text-[12px] font-semibold leading-relaxed text-[#202223]"
          compact
        />
        {memory.source_title ? (
          <p className="mt-2 truncate text-[10px] font-medium text-[#85888b]">
            {memory.source_title}
          </p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={onArchive}
        disabled={archiving}
        className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border border-transparent text-[#7d8285] opacity-100 transition hover:border-[#d8dcde] hover:bg-white hover:text-[#9b4c51] disabled:cursor-not-allowed disabled:opacity-50 md:opacity-0 md:group-hover:opacity-100"
        aria-label="Remove memory from active use"
        title="Remove from active memory"
      >
        <Archive size={15} />
      </button>
    </article>
  );
}

function formatRecentDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recent";
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function SearchContext({
  query,
  count,
  topScore,
}: {
  query: string | null;
  count: number;
  topScore: number | null;
}) {
  return (
    <div className="h-full px-5 py-6">
      <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
        Search signal
      </p>
      {query ? (
        <>
          <blockquote className="mt-4 border-l-2 border-[#111111] pl-3 text-[12px] font-semibold leading-relaxed">
            {query}
          </blockquote>
          <div className="mt-7 grid grid-cols-2 gap-2">
            <Metric label="Found" value={String(count)} />
            <Metric
              label="Closest"
              value={topScore === null ? "—" : `${Math.round(topScore * 100)}%`}
            />
          </div>
        </>
      ) : (
        <p className="mt-4 text-[11px] font-semibold leading-relaxed text-[#777b7e]">
          Ask in your own words. Crowscap searches the meaning held inside each
          memory.
        </p>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[#e1e3e4] bg-white p-3">
      <p className="text-[9px] font-extrabold uppercase text-[#929598]">
        {label}
      </p>
      <p className="mt-1 text-[18px] font-[760]">{value}</p>
    </div>
  );
}
