import { useState, useEffect, useCallback } from "react";
import { searchMemories } from "@/api/search";
import { deleteMemory, getRecentMemories } from "@/api/memories";
import type { SearchResponse, RecentMemory } from "@/types/api";

export function useSearch() {
  const [query, setQuery] = useState("");
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [recent, setRecent] = useState<RecentMemory[]>([]);
  const [recentOffset, setRecentOffset] = useState(0);
  const [recentHasMore, setRecentHasMore] = useState(false);
  const [loadingRecent, setLoadingRecent] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchRecent = useCallback(async (offset: number) => {
    setLoadingRecent(true);
    setError(null);
    try {
      const res = await getRecentMemories(20, offset);
      setRecent((prev) => (offset === 0 ? res.memories : [...prev, ...res.memories]));
      setRecentOffset(offset + res.memories.length);
      setRecentHasMore(res.has_more);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load recent memories.");
    } finally {
      setLoadingRecent(false);
    }
  }, []);

  useEffect(() => {
    fetchRecent(0);
  }, [fetchRecent]);

  const executeSearch = async (text: string) => {
    const trimmed = text.trim();
    if (trimmed.length < 2) return;
    setSearching(true);
    setError(null);
    try {
      const res = await searchMemories({ query: trimmed });
      setSearchResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search request failed.");
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setQuery("");
    setSearchResult(null);
  };

  const handleDelete = async (memoryId: string) => {
    if (deletingId) return;
    setDeletingId(memoryId);
    try {
      await deleteMemory(memoryId);
      setRecent((prev) => prev.filter((m) => m.memory_id !== memoryId));
      if (searchResult) {
        setSearchResult((prev) =>
          prev
            ? {
                ...prev,
                results: prev.results.filter((m) => m.memory_id !== memoryId),
                returned_count: Math.max(0, prev.returned_count - 1),
              }
            : null
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete memory.");
    } finally {
      setDeletingId(null);
    }
  };

  return {
    query,
    setQuery,
    searchResult,
    searching,
    recent,
    recentHasMore,
    loadingRecent,
    error,
    deletingId,
    executeSearch,
    clearSearch,
    loadMoreRecent: () => fetchRecent(recentOffset),
    handleDelete,
  };
}
