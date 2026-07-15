"use client";

import { ArrowRight, Search, Sparkles, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { MemoryCardView } from "@/components/memory/memory-card";
import { AppShell } from "@/components/shell/app-shell";
import { getDueRecalls, searchMemories } from "@/lib/api";
import type { SearchResponse } from "@/lib/types";

export function SearchWorkspace() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dueCount, setDueCount] = useState(0);

  useEffect(() => {
    getDueRecalls(1)
      .then((response) => setDueCount(response.due_count))
      .catch(() => setDueCount(0));
  }, []);

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

  return (
    <AppShell
      dueCount={dueCount}
      title="Search memory"
      subtitle="Find meaning, not just matching words"
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
              <Sparkles size={16} />
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
          ) : (
            <div className="mt-12 grid gap-2 sm:grid-cols-2">
              {[
                "What do I know about distribution?",
                "Find ideas I saved about product design",
                "Where have my sources disagreed?",
                "What have I learned but not applied?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setQuery(suggestion)}
                  className="min-h-16 rounded-lg border border-[#e0e2e3] bg-[#fafafa] px-4 py-3 text-left text-[11px] font-semibold leading-relaxed transition hover:border-[#c8ccce] hover:bg-white"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
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
