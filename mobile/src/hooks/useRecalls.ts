import { useState, useEffect, useCallback } from "react";
import { getDueRecalls, answerRecall } from "@/api/recalls";
import type { RecallDueResponse, RecallMemory, RecallAnswerResponse } from "@/types/api";
import { scheduleLocalNotification } from "@/utils/notifications";

export function useRecalls() {
  const [data, setData] = useState<RecallDueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [answering, setAnswering] = useState(false);
  const [evaluation, setEvaluation] = useState<RecallAnswerResponse | null>(null);

  const fetchDue = useCallback(async () => {
    try {
      setError(null);
      const res = await getDueRecalls(50);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch due recalls.");
    } finally {
      setLoading(false);
    }
  }, []);



  useEffect(() => {
    fetchDue();
  }, [fetchDue]);

  const selectedMemory: RecallMemory | null =
    data?.memories.find((m) => m.memory_id === selectedId) ?? null;

  const submitAnswerFor = async (memoryId: string, answerText: string, selfRating: number) => {
    if (answering) return;
    setAnswering(true);
    setError(null);
    try {
      const evalRes = await answerRecall(memoryId, {
        answer: answerText,
        self_rating: selfRating,
      });
      setEvaluation(evalRes);
      await fetchDue();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit recall answer.");
    } finally {
      setAnswering(false);
    }
  };

  const submitAnswer = async (answerText: string, selfRating: number) => {
    if (!selectedMemory) return;
    await submitAnswerFor(selectedMemory.memory_id, answerText, selfRating);
  };

  const nextRecall = () => {
    setEvaluation(null);
    if (!data || data.memories.length === 0) return;
    const currentIndex = data.memories.findIndex((m) => m.memory_id === selectedId);
    if (currentIndex >= 0 && currentIndex < data.memories.length - 1) {
      setSelectedId(data.memories[currentIndex + 1].memory_id);
    } else {
      setSelectedId(data.memories[0]?.memory_id ?? null);
    }
  };

  const clearSelected = () => {
    setSelectedId(null);
    setEvaluation(null);
  };

  return {
    data,
    loading,
    error,
    selectedMemory,
    selectedId,
    setSelectedId,
    answering,
    evaluation,
    submitAnswer,
    submitAnswerFor,
    nextRecall,
    clearSelected,
    refresh: fetchDue,
  };
}
