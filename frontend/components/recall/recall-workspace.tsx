"use client";

import {
  ArrowUp,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  Clock3,
  FileText,
  GitCompareArrows,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/shell/app-shell";
import type { AppShellUser } from "@/components/shell/app-shell";
import {
  completeReminder,
  getDueRecalls,
  getSourceContent,
  snoozeReminder,
  submitQuickRecall,
  submitRecallAnswer,
} from "@/lib/api";
import {
  formatFriendlyDateTime,
  formatRelativeOverdue,
  humanizeRelationshipText,
} from "@/lib/chat";
import type {
  DueRecall,
  DueReminder,
  DueRecallsResponse,
  RecallAnswerResponse,
  RecallQuickAction,
  RecallQuickResponse,
  SourceContentResponse,
} from "@/lib/types";

export function RecallWorkspace({
  requestedMemoryId,
  user,
}: {
  requestedMemoryId?: string;
  user: AppShellUser;
}) {
  const [data, setData] = useState<DueRecallsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [selfRating, setSelfRating] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [evaluation, setEvaluation] = useState<RecallAnswerResponse | null>(null);
  const [source, setSource] = useState<SourceContentResponse | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [showDeepReview, setShowDeepReview] = useState(false);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [selectedReminderId, setSelectedReminderId] = useState<string | null>(null);
  const [completingReminder, setCompletingReminder] = useState(false);
  const [snoozingReminder, setSnoozingReminder] = useState(false);
  const [quickSubmitting, setQuickSubmitting] =
    useState<RecallQuickAction | null>(null);
  const [quickResult, setQuickResult] = useState<RecallQuickResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    const refreshDue = (isInitial = false) => {
      getDueRecalls(50)
        .then((response) => {
          if (!cancelled) setData(response);
        })
        .catch((requestError) => {
          if (cancelled) return;
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Recall is unavailable.",
          );
        })
        .finally(() => {
          if (!cancelled && isInitial) setLoading(false);
        });
    };

    refreshDue(true);
    const intervalId = window.setInterval(() => refreshDue(false), 30_000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const selectedReminder = useMemo(() => {
    if (requestedMemoryId || !data?.reminders.length) return null;
    return (
      data.reminders.find(
        (reminder) => reminder.reminder_id === selectedReminderId,
      ) ?? data.reminders[0]
    );
  }, [data, requestedMemoryId, selectedReminderId]);

  const selected = useMemo(() => {
    if (!data?.memories.length) return null;
    if (selectedReminder && !requestedMemoryId) return null;
    if (!requestedMemoryId) return data.memories[0];
    return (
      data.memories.find(
        (memory) => memory.memory_id === requestedMemoryId,
      ) ?? data.memories[0]
    );
  }, [data, requestedMemoryId, selectedReminder]);

  useEffect(() => {
    setAnswer("");
    setSelfRating(3);
    setEvaluation(null);
    setError(null);
    setSource(null);
    setShowOriginal(false);
    setShowDeepReview(false);
    setQuickSubmitting(null);
    setQuickResult(null);
    setCompletingReminder(false);
    setSnoozingReminder(false);
  }, [selected?.memory_id, selectedReminder?.reminder_id]);

  async function completeSelectedReminder() {
    if (!selectedReminder || completingReminder) return;

    setCompletingReminder(true);
    setError(null);
    try {
      await completeReminder(selectedReminder.reminder_id);
      setData((current) => {
        if (!current) return current;
        return {
          ...current,
          due_count: Math.max(0, current.due_count - 1),
          reminders: current.reminders.filter(
            (reminder) => reminder.reminder_id !== selectedReminder.reminder_id,
          ),
        };
      });
      setSelectedReminderId(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The reminder could not be marked done.",
      );
    } finally {
      setCompletingReminder(false);
    }
  }

  async function snoozeSelectedReminder() {
    if (!selectedReminder || snoozingReminder) return;

    setSnoozingReminder(true);
    setError(null);
    try {
      await snoozeReminder(selectedReminder.reminder_id, 60);
      setData((current) => {
        if (!current) return current;
        return {
          ...current,
          due_count: Math.max(0, current.due_count - 1),
          reminders: current.reminders.filter(
            (reminder) => reminder.reminder_id !== selectedReminder.reminder_id,
          ),
        };
      });
      setSelectedReminderId(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The reminder could not be snoozed.",
      );
    } finally {
      setSnoozingReminder(false);
    }
  }

  async function toggleOriginal() {
    if (!selected) return;
    if (showOriginal) {
      setShowOriginal(false);
      return;
    }

    setShowOriginal(true);
    if (source) return;

    setSourceLoading(true);
    try {
      setSource(await getSourceContent(selected.source_id));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The original source could not be loaded.",
      );
    } finally {
      setSourceLoading(false);
    }
  }

  async function submitAnswer() {
    if (!selected || answer.trim().length < 3 || submitting || evaluation) return;

    setSubmitting(true);
    setError(null);
    try {
      const response = await submitRecallAnswer(
        selected.memory_id,
        answer.trim(),
        selfRating,
      );
      setEvaluation(response);
      setData((current) =>
        current
          ? {
              ...current,
              due_count: Math.max(0, current.due_count - 1),
            }
          : current,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Your recall answer could not be evaluated.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function submitQuick(action: RecallQuickAction) {
    if (!selected || quickSubmitting || quickResult) return;

    setQuickSubmitting(action);
    setError(null);
    try {
      const response = await submitQuickRecall(selected.memory_id, action);
      setQuickResult(response);
      setData((current) =>
        current
          ? {
              ...current,
              due_count: Math.max(0, current.due_count - 1),
            }
          : current,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "This recall action could not be saved.",
      );
    } finally {
      setQuickSubmitting(null);
    }
  }

  function showNextThought() {
    if (!selected) return;
    setData((current) =>
      current
        ? {
            ...current,
            memories: current.memories.filter(
              (memory) => memory.memory_id !== selected.memory_id,
            ),
          }
        : current,
    );
    setQuickResult(null);
  }

  return (
    <AppShell
      dueCount={data?.due_count ?? 0}
      title="Recall"
      user={user}
      subtitle={
        selected
          ? "One useful nudge, not a queue"
          : selectedReminder
            ? "A reminder is ready"
            : "Nothing due"
      }
      context={
        <RecallContext
          memories={data?.memories ?? []}
          reminders={data?.reminders ?? []}
          selectedId={selected?.memory_id ?? null}
          selectedReminderId={selectedReminder?.reminder_id ?? null}
          onSelectReminder={setSelectedReminderId}
        />
      }
    >
      <div className="conversation-scroll flex-1 overflow-y-auto px-4 pb-36 pt-8 md:px-8 md:pb-10 md:pt-12">
        <div className="mx-auto max-w-[720px]">
          {loading ? (
            <p className="text-[12px] font-semibold text-[#727679]">
              Gathering what is ready
            </p>
          ) : null}
          {error ? (
            <p className="text-[12px] font-semibold text-[#9b4c51]">{error}</p>
          ) : null}
          {!loading && !error && !selected && !selectedReminder ? (
            <EmptyRecall />
          ) : null}

          {!loading && !error && selectedReminder ? (
            <ReminderDue
              reminder={selectedReminder}
              completing={completingReminder}
              snoozing={snoozingReminder}
              onComplete={completeSelectedReminder}
              onSnooze={snoozeSelectedReminder}
            />
          ) : null}

          {selected ? (
            <div className="rise-in">
              <div className="flex items-center gap-2 text-[#2d7058]">
                <Sparkles size={15} />
                <span className="text-[10px] font-extrabold uppercase">
                  A thought is ready
                </span>
              </div>
              <h2 className="mt-5 max-w-[650px] text-[24px] font-[750] leading-[1.35] md:text-[30px]">
                {selected.summary ?? selected.content}
              </h2>
              <p className="mt-3 text-[11px] font-semibold text-[#85888b]">
                Saved from {selected.source_title ?? "a saved source"} -{" "}
                {formatRelativeOverdue(selected.overdue_seconds)}
              </p>

              <div className="mt-8 rounded-lg border border-[#d9dcde] bg-[#f8f9f9] p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[10px] font-extrabold uppercase text-[#85888b]">
                    The idea
                  </p>
                  <button
                    type="button"
                    onClick={toggleOriginal}
                    className="flex items-center gap-1.5 text-[10px] font-extrabold text-[#555a5d] transition hover:text-[#111111]"
                  >
                    <FileText size={13} />
                    {showOriginal ? "Show memory" : "View original"}
                  </button>
                </div>
                {showOriginal ? (
                  sourceLoading ? (
                    <p className="mt-3 text-[12px] font-medium text-[#85888b]">
                      Loading the exact source...
                    </p>
                  ) : source?.original_content ? (
                    <p className="mt-3 max-h-[460px] overflow-y-auto whitespace-pre-wrap break-words text-[13px] font-medium leading-6">
                      {source.original_content}
                    </p>
                  ) : (
                    <p className="mt-3 text-[12px] font-medium leading-relaxed text-[#74777a]">
                      This earlier capture does not have its original text stored.
                      Save the same source once more to restore it.
                    </p>
                  )
                ) : (
                  <p className="mt-3 text-[15px] font-semibold leading-relaxed">
                    {selected.content}
                  </p>
                )}
              </div>

              {selected.epistemic_caution ? (
                <div className="mt-4 flex items-start gap-2 rounded-lg border border-[#eadbbd] bg-[#fcf6ea] px-4 py-3 text-[#85571e]">
                  <CircleAlert className="mt-0.5 shrink-0" size={14} />
                  <p className="text-[10px] font-semibold leading-relaxed">
                    {selected.epistemic_caution}
                  </p>
                </div>
              ) : null}

              <div className="mt-5 rounded-lg border border-[#d7e5dc] bg-[#f1f7f4] p-5">
                <p className="text-[10px] font-extrabold uppercase text-[#2d7058]">
                  Quick check
                </p>
                <p className="mt-2 text-[13px] font-semibold leading-relaxed text-[#3f5d51]">
                  Does this still feel useful for what you are doing now?
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <QuickRecallButton
                    label="Still useful"
                    action="still_relevant"
                    activeAction={quickSubmitting}
                    disabled={Boolean(quickResult)}
                    onClick={submitQuick}
                  />
                  <QuickRecallButton
                    label="I used it"
                    action="applied"
                    activeAction={quickSubmitting}
                    disabled={Boolean(quickResult)}
                    onClick={submitQuick}
                  />
                  <QuickRecallButton
                    label="Not now"
                    action="not_now"
                    activeAction={quickSubmitting}
                    disabled={Boolean(quickResult)}
                    onClick={submitQuick}
                  />
                  <button
                    type="button"
                    onClick={() => setShowDeepReview((value) => !value)}
                    className="rounded-md border border-[#d7dadc] bg-white px-3 py-2 text-[11px] font-extrabold text-[#4d5255] transition hover:border-[#9fa4a7]"
                  >
                    {showDeepReview ? "Hide deeper review" : "Review deeper"}
                  </button>
                </div>
              </div>

              {quickResult ? (
                <QuickRecallResult
                  result={quickResult}
                  onShowNext={showNextThought}
                />
              ) : null}

              {showDeepReview ? (
                <div className="mt-5 rounded-lg border border-[#cfd2d4] bg-white p-2 shadow-[0_14px_42px_rgba(17,17,17,0.07)]">
                  <div className="px-3 pt-3">
                    <p className="text-[10px] font-extrabold uppercase text-[#85888b]">
                      Sit with it
                    </p>
                    <p className="mt-1 text-[12px] font-semibold leading-relaxed text-[#606568]">
                      {selected.recall_prompt}
                    </p>
                  </div>
                  <textarea
                    rows={5}
                    value={answer}
                    onChange={(event) => setAnswer(event.target.value)}
                    placeholder="Write what comes to mind..."
                    className="w-full resize-none bg-transparent px-3 py-3 text-[13px] font-medium leading-relaxed outline-none placeholder:text-[#a0a3a5]"
                  />
                  <div className="flex items-center px-1 pb-1">
                    <span className="text-[9px] font-bold uppercase text-[#939699]">
                      Your own words
                    </span>
                    <div className="ml-auto mr-2 flex items-center rounded-md bg-[#f1f2f3] p-0.5">
                      {[1, 2, 3, 4].map((rating) => (
                        <button
                          key={rating}
                          type="button"
                          title={`Self-rating ${rating} of 4`}
                          onClick={() => setSelfRating(rating)}
                          className={`flex size-7 items-center justify-center rounded text-[9px] font-extrabold ${
                            selfRating === rating
                              ? "bg-white text-[#111111] shadow-sm"
                              : "text-[#8a8d90]"
                          }`}
                        >
                          {rating}
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={submitAnswer}
                      disabled={
                        answer.trim().length < 3 ||
                        submitting ||
                        Boolean(evaluation)
                      }
                      aria-label="Reflect on answer"
                      className="ml-auto flex size-9 items-center justify-center rounded-md bg-[#111111] text-white disabled:bg-[#d2d4d5]"
                    >
                      <ArrowUp size={17} />
                    </button>
                  </div>
                </div>
              ) : null}

              {evaluation ? (
                <Reflection evaluation={evaluation} />
              ) : selected.relationships.length > 0 ? (
                <div className="mt-6 flex items-start gap-3 border-t border-[#e3e5e6] pt-5">
                  <GitCompareArrows
                    className="mt-0.5 shrink-0 text-[#9a611e]"
                    size={15}
                  />
                  <div>
                    <p className="text-[10px] font-extrabold uppercase text-[#9a611e]">
                      Another saved idea may help
                    </p>
                    <p className="mt-1 text-[11px] font-semibold leading-relaxed text-[#6f6253]">
                      {selected.relationships[0].explanation
                        ? humanizeRelationshipText(
                            selected.relationships[0].explanation,
                          )
                        : "This idea is worth comparing with something else you saved."}
                    </p>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}

function QuickRecallButton({
  label,
  action,
  activeAction,
  disabled,
  onClick,
}: {
  label: string;
  action: RecallQuickAction;
  activeAction: RecallQuickAction | null;
  disabled: boolean;
  onClick: (action: RecallQuickAction) => void;
}) {
  const active = activeAction === action;

  return (
    <button
      type="button"
      onClick={() => onClick(action)}
      disabled={disabled || activeAction !== null}
      className="rounded-md border border-[#cfd8d3] bg-white px-3 py-2 text-[11px] font-extrabold text-[#244f42] transition hover:border-[#9eb9ad] hover:bg-[#f7fbf9] disabled:cursor-not-allowed disabled:border-[#d9dddb] disabled:bg-[#eef0ef] disabled:text-[#8c9390]"
    >
      {active ? "Saving..." : label}
    </button>
  );
}

function QuickRecallResult({
  result,
  onShowNext,
}: {
  result: RecallQuickResponse;
  onShowNext: () => void;
}) {
  return (
    <div className="mt-4 rounded-lg border border-[#d5e4db] bg-[#f0f7f3] p-5 rise-in">
      <div className="flex items-start gap-3">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-white text-[#2d7058] shadow-sm">
          <CircleCheck size={16} />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-extrabold uppercase text-[#2d7058]">
            Noted
          </p>
          <p className="mt-1 text-[12px] font-semibold leading-relaxed text-[#43564e]">
            {result.feedback}
          </p>
          <p className="mt-2 text-[10px] font-bold uppercase text-[#759084]">
            Back again {formatFriendlyDateTime(result.next_due_at)}
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onShowNext}
        className="mt-4 inline-flex items-center gap-1.5 text-[11px] font-extrabold text-[#2d7058]"
      >
        Show next thought <ChevronRight size={14} />
      </button>
    </div>
  );
}

function ReminderDue({
  reminder,
  completing,
  snoozing,
  onComplete,
  onSnooze,
}: {
  reminder: DueReminder;
  completing: boolean;
  snoozing: boolean;
  onComplete: () => void;
  onSnooze: () => void;
}) {
  return (
    <div className="rise-in">
      <div className="flex items-center gap-2 text-[#2d7058]">
        <Clock3 size={15} />
        <span className="text-[10px] font-extrabold uppercase">
          Reminder ready
        </span>
      </div>
      <h2 className="mt-5 max-w-[650px] text-[24px] font-[750] leading-[1.35] md:text-[30px]">
        {reminder.content}
      </h2>
      <p className="mt-3 text-[11px] font-semibold text-[#85888b]">
        Due {formatFriendlyDateTime(reminder.due_at)} -{" "}
        {formatRelativeOverdue(reminder.overdue_seconds)} -{" "}
        {reminder.save_as_memory
          ? "connected to a saved memory"
          : "not saved as memory"}
      </p>
      <div className="mt-8 rounded-lg border border-[#d7e5dc] bg-[#f1f7f4] px-4 py-3 text-[#2d7058]">
        <p className="text-[9px] font-extrabold uppercase">
          One-time reminder
        </p>
        <p className="mt-2 text-[12px] font-semibold leading-relaxed text-[#3f5d51]">
          This is a nudge, not recall history. Mark it done and it leaves the
          active recall surface.
        </p>
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onComplete}
          disabled={completing || snoozing}
          className="inline-flex items-center gap-2 rounded-lg border border-[#c8dcd2] bg-white px-4 py-3 text-[11px] font-extrabold text-[#245e4b] transition hover:border-[#9ebfad] hover:bg-[#f7fbf9] disabled:cursor-not-allowed disabled:border-[#d9dddb] disabled:bg-[#eef0ef] disabled:text-[#8c9390] [&_svg]:stroke-[#245e4b]"
        >
          <CircleCheck size={14} />
          {completing ? "Marking done..." : "Done"}
        </button>
        <button
          type="button"
          onClick={onSnooze}
          disabled={completing || snoozing}
          className="inline-flex items-center gap-2 rounded-lg border border-[#d7dadc] bg-white px-4 py-3 text-[11px] font-extrabold text-[#555a5d] transition hover:border-[#aeb3b5] hover:bg-[#f7f8f8] disabled:cursor-not-allowed disabled:border-[#d9dddb] disabled:bg-[#eef0ef] disabled:text-[#8c9390] [&_svg]:stroke-[#555a5d]"
        >
          <Clock3 size={14} />
          {snoozing ? "Snoozing..." : "Snooze 1h"}
        </button>
      </div>
    </div>
  );
}

function Reflection({
  evaluation,
}: {
  evaluation: RecallAnswerResponse;
}) {
  return (
    <div className="mt-6 rounded-lg border border-[#d5e4db] bg-[#f0f7f3] p-5 rise-in">
      <div className="flex items-center gap-2 text-[#2d7058]">
        <CircleCheck size={16} />
        <p className="text-[10px] font-extrabold uppercase">Reflection saved</p>
      </div>
      <p className="mt-3 text-[12px] font-semibold leading-relaxed text-[#43564e]">
        {evaluation.feedback}
      </p>
      <div className="mt-4 border-t border-[#d8e7de] pt-4">
        <p className="text-[9px] font-extrabold uppercase text-[#2d7058]">
          What this idea means
        </p>
        <p className="mt-2 text-[11px] font-semibold leading-relaxed text-[#4b6258]">
          {evaluation.understanding_summary}
        </p>
      </div>
      {evaluation.knowledge_gaps.length > 0 ? (
        <FeedbackList
          label="Understanding gaps"
          items={evaluation.knowledge_gaps}
        />
      ) : null}
      {evaluation.context_to_consider.length > 0 ? (
        <FeedbackList
          label="Context to keep in view"
          items={evaluation.context_to_consider}
        />
      ) : null}
      {evaluation.next_question ? (
        <div className="mt-4 border-t border-[#d8e7de] pt-4">
          <p className="text-[9px] font-extrabold uppercase text-[#2d7058]">
            Think one step further
          </p>
          <p className="mt-2 text-[11px] font-semibold leading-relaxed text-[#4b6258]">
            {evaluation.next_question}
          </p>
        </div>
      ) : null}
      <p className="mt-4 text-[9px] font-bold uppercase text-[#759084]">
        Next review {new Date(evaluation.next_due_at).toLocaleDateString()}
      </p>
    </div>
  );
}

function FeedbackList({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="mt-4 border-t border-[#d8e7de] pt-4">
      <p className="text-[9px] font-extrabold uppercase text-[#2d7058]">
        {label}
      </p>
      <ul className="mt-2 space-y-1.5">
        {items.map((item) => (
          <li
            key={item}
            className="text-[11px] font-medium leading-relaxed text-[#53685f]"
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function EmptyRecall() {
  return (
    <div className="py-16 text-center">
      <div className="mx-auto flex size-11 items-center justify-center rounded-full bg-[#eef3f0] text-[#2d7058]">
        <CircleCheck size={20} />
      </div>
      <h2 className="mt-5 text-[20px] font-[750]">Your memory is clear.</h2>
      <p className="mx-auto mt-2 max-w-sm text-[12px] font-medium leading-relaxed text-[#7c8083]">
        Nothing needs your attention right now.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex items-center gap-1 text-[11px] font-extrabold"
      >
        Return to chat <ChevronRight size={14} />
      </Link>
    </div>
  );
}

function RecallContext({
  memories,
  reminders,
  selectedId,
  selectedReminderId,
  onSelectReminder,
}: {
  memories: DueRecall[];
  reminders: DueReminder[];
  selectedId: string | null;
  selectedReminderId: string | null;
  onSelectReminder: (reminderId: string) => void;
}) {
  return (
    <div className="h-full overflow-y-auto px-5 py-6">
      <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
        More to revisit
      </p>
      <h2 className="mt-2 text-[20px] font-[750] leading-tight">
        One at a time.
      </h2>
      <p className="mt-2 text-[11px] font-semibold leading-relaxed text-[#777b7e]">
        Crowscap keeps the backlog quiet and brings forward the next useful
        thing.
      </p>
      <div className="mt-6 space-y-1">
        {reminders.slice(0, 8).map((reminder, index) => (
          <button
            key={reminder.reminder_id}
            type="button"
            onClick={() => onSelectReminder(reminder.reminder_id)}
            className={`block w-full rounded-lg border px-3 py-3 text-left transition ${
              reminder.reminder_id === selectedReminderId
                ? "border-[#c6d9ce] bg-[#edf5f1]"
                : "border-transparent hover:border-[#e0e2e3] hover:bg-white"
            }`}
          >
            <p className="text-[9px] font-extrabold uppercase text-[#2d7058]">
              {String(index + 1).padStart(2, "0")} - reminder
            </p>
            <p className="mt-1 line-clamp-2 text-[11px] font-semibold leading-relaxed">
              {reminder.content}
            </p>
            <p className="mt-1 text-[9px] font-bold text-[#85888b]">
              Due {formatFriendlyDateTime(reminder.due_at)}
            </p>
          </button>
        ))}
        {memories.slice(0, 12).map((memory, index) => (
          <Link
            key={memory.memory_id}
            href={`/recall/${memory.memory_id}`}
            className={`block rounded-lg border px-3 py-3 transition ${
              memory.memory_id === selectedId
                ? "border-[#c6d9ce] bg-[#edf5f1]"
                : "border-transparent hover:border-[#e0e2e3] hover:bg-white"
            }`}
          >
            <p className="text-[9px] font-extrabold uppercase text-[#85888b]">
              {String(reminders.length + index + 1).padStart(2, "0")} -{" "}
              {memory.memory_type}
            </p>
            <p className="mt-1 line-clamp-2 text-[11px] font-semibold leading-relaxed">
              {memory.summary ?? memory.content}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
