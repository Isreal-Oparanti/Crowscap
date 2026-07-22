"use client";

import {
  ArrowUp,
  BadgeCheck,
  BookOpenCheck,
  Check,
  CheckCheck,
  ChevronRight,
  Clipboard,
  Clock3,
  CircleAlert,
  FileText,
  GitCompareArrows,
  Link2,
  Paperclip,
  Search,
  SlidersHorizontal,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { MemoryCardView } from "@/components/memory/memory-card";
import { AppShell } from "@/components/shell/app-shell";
import { BrandIcon } from "@/components/ui/brand-icon";
import { MarkdownText } from "@/components/ui/markdown-text";
import {
  getCurrentConversation,
  getDueRecalls,
  sendChatMessage,
  uploadPdfToChat,
} from "@/lib/api";
import {
  formatFriendlyDateTime,
  formatTranscriptForDisplay,
  humanizeIntent,
  humanizeRelationshipText,
  parseReferenceContent,
  sourceContentLabel,
  sourceTypeLabel,
} from "@/lib/chat";
import type { AppShellUser } from "@/components/shell/app-shell";
import type {
  BeliefAuditResponse,
  CaptureResponse,
  ChatResponse,
  ConversationTurn,
  DueReminder,
  DueRecallsResponse,
  PersistedChatMessage,
  SearchResponse,
} from "@/lib/types";

type ChatMessage =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "assistant";
      kind: "text";
      text: string;
    }
  | {
      id: string;
      role: "assistant";
      kind: "capture";
      text: string;
      data: CaptureResponse;
    }
  | {
      id: string;
      role: "assistant";
      kind: "answer";
      text: string;
      data: ChatResponse;
    }
  | {
      id: string;
      role: "assistant";
      kind: "audit";
      text: string;
      data: BeliefAuditResponse;
    }
  | {
      id: string;
      role: "assistant";
      kind: "reminder";
      text: string;
      data: ChatResponse;
    }
  | {
      id: string;
      role: "assistant";
      kind: "error";
      text: string;
      retryText?: string;
    };

function openingMessagesFor(user: AppShellUser): ChatMessage[] {
  const name = user.name?.split(/\s+/)[0] ?? "there";
  return [
    {
      id: "opening",
      role: "assistant",
      kind: "text",
      text: `Welcome back, ${name}. What has your attention today?`,
    },
  ];
}

const chatActions: ChatResponse["action"][] = [
  "acknowledge",
  "conversation",
  "capture",
  "answer",
  "audit",
  "forget",
  "reminder",
  "self",
  "recent",
];

function normalizeChatResponse(
  raw: Partial<ChatResponse> | null | undefined,
  fallbackMessage: string,
): ChatResponse {
  const action = chatActions.includes(raw?.action as ChatResponse["action"])
    ? (raw?.action as ChatResponse["action"])
    : "conversation";

  return {
    action,
    message:
      typeof raw?.message === "string" && raw.message.trim()
        ? raw.message
        : fallbackMessage,
    conversation_id:
      typeof raw?.conversation_id === "string" ? raw.conversation_id : null,
    user_message_id:
      typeof raw?.user_message_id === "string" ? raw.user_message_id : null,
    assistant_message_id:
      typeof raw?.assistant_message_id === "string"
        ? raw.assistant_message_id
        : null,
    saved: Boolean(raw?.saved),
    capture: raw?.capture ?? null,
    evidence: Array.isArray(raw?.evidence) ? raw.evidence : [],
    knowledge_gaps: Array.isArray(raw?.knowledge_gaps)
      ? raw.knowledge_gaps
      : [],
    tensions: Array.isArray(raw?.tensions) ? raw.tensions : [],
    next_step: typeof raw?.next_step === "string" ? raw.next_step : null,
    audit: raw?.audit ?? null,
    reminder: raw?.reminder ?? null,
    preference_updates: Array.isArray(raw?.preference_updates)
      ? raw.preference_updates
      : [],
    preferences: raw?.preferences ?? null,
  };
}

function conversationTurnsFrom(messages: ChatMessage[]): ConversationTurn[] {
  return messages
    .filter((message) => !(message.role === "assistant" && message.kind === "error"))
    .map<ConversationTurn>((message) => ({
      role: message.role,
      content: message.text,
    }))
    .slice(-12);
}

export function ChatWorkspace({ user }: { user: AppShellUser }) {
  const userKey = user.id ?? user.email ?? user.name ?? "anonymous";
  const openingMessages = useMemo(() => openingMessagesFor(user), [
    userKey,
    user.name,
    user.email,
  ]);
  const [messages, setMessages] = useState<ChatMessage[]>(openingMessages);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [working, setWorking] = useState(false);
  const [due, setDue] = useState<DueRecallsResponse | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setMessages(openingMessages);
    setConversationId(null);
    setDraft("");
    setAttachedFile(null);
    setWorking(false);
    setDue(null);

    const refreshDue = () => {
      if (document.visibilityState === "hidden") return;
      getDueRecalls(8)
        .then((response) => {
          if (!cancelled) setDue(response);
        })
        .catch(() => undefined);
    };

    refreshDue();
    const intervalId = window.setInterval(refreshDue, 300_000);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") refreshDue();
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    getCurrentConversation()
      .then((conversation) => {
        if (cancelled) return;
        if (!conversation) return;
        setConversationId(conversation.id);
        const restored = conversation.messages.map(hydratePersistedMessage);
        setMessages(restored.length > 0 ? restored : openingMessages);
      })
      .catch(() => {
        if (cancelled) return;
        setConversationId(null);
      });

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [openingMessages, userKey]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, working]);

  const contextMemories = useMemo(() => {
    const latestAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");
    if (
      !latestAssistant ||
      latestAssistant.kind === "text" ||
      latestAssistant.kind === "error"
    ) {
      return [];
    }
    return latestAssistant.kind === "capture"
      ? latestAssistant.data.memories.slice(0, 3)
      : latestAssistant.kind === "audit"
        ? latestAssistant.data.memories.slice(0, 3)
        : latestAssistant.kind === "reminder"
          ? (latestAssistant.data.capture?.memories.slice(0, 3) ?? [])
        : latestAssistant.data.evidence.slice(0, 3);
  }, [messages]);

  async function sendMessage() {
    const text = draft.trim();
    if ((!text && !attachedFile) || working) return;

    if (attachedFile) {
      return uploadPdf(attachedFile, text);
    }

    await sendTextMessage(text);
  }

  async function retryTextMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || working) return;
    await sendTextMessage(trimmed);
  }

  async function sendTextMessage(text: string) {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text,
    };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setWorking(true);

    try {
      const history = conversationTurnsFrom(messages);
      const response = normalizeChatResponse(
        await sendChatMessage(text, history, conversationId),
        "I heard you.",
      );
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      setMessages((current) => [
        ...current,
        response.action === "capture" && response.capture
          ? {
              id: response.assistant_message_id ?? crypto.randomUUID(),
              role: "assistant",
              kind: "capture",
              text: response.message,
              data: response.capture,
            }
          : response.preference_updates.length > 0 ||
              response.action === "answer" ||
              response.action === "forget" ||
              response.action === "self"
            ? {
                id: response.assistant_message_id ?? crypto.randomUUID(),
                role: "assistant",
                kind: "answer",
                text: response.message,
                data: response,
              }
            : response.action === "audit" && response.audit
              ? {
                  id: response.assistant_message_id ?? crypto.randomUUID(),
                  role: "assistant",
                  kind: "audit",
                  text: response.message,
                  data: response.audit,
                }
            : response.action === "reminder" && response.reminder
              ? {
                  id: response.assistant_message_id ?? crypto.randomUUID(),
                  role: "assistant",
                  kind: "reminder",
                  text: response.message,
                  data: response,
                }
            : {
                id: response.assistant_message_id ?? crypto.randomUUID(),
                role: "assistant",
                kind: "text",
                text: response.message,
              },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "error",
          text:
            error instanceof Error
              ? error.message
              : "I could not complete that thought.",
          retryText: text,
        },
      ]);
    } finally {
      setWorking(false);
      textareaRef.current?.focus();
    }
  }

  async function uploadPdf(file: File, draftText: string) {
    if (working) return;

    const isPdf =
      file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "error",
          text: "Please choose a PDF file. Crowscap currently supports text-based PDFs only.",
        },
      ]);
      setAttachedFile(null);
      return;
    }

    const maxPdfSizeBytes = 10 * 1024 * 1024;
    if (file.size > maxPdfSizeBytes) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "error",
          text: "That PDF is larger than 10MB. Try a smaller text-based PDF for now.",
        },
      ]);
      setAttachedFile(null);
      return;
    }

    const displayMessage = draftText.trim()
      ? `${draftText.trim()}\n\n[Attached PDF: ${file.name}]`
      : `Uploaded PDF: ${file.name}`;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: displayMessage,
    };
    setMessages((current) => [...current, userMessage]);
    setWorking(true);
    setDraft("");
    setAttachedFile(null);

    try {
      const response = normalizeChatResponse(
        await uploadPdfToChat(file, draftText, conversationId),
        "I processed the PDF.",
      );
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      setMessages((current) => [
        ...current,
        response.capture
          ? {
              id: response.assistant_message_id ?? crypto.randomUUID(),
              role: "assistant",
              kind: "capture",
              text: response.message,
              data: response.capture,
            }
          : {
              id: response.assistant_message_id ?? crypto.randomUUID(),
              role: "assistant",
              kind: "text",
              text: response.message,
            },
      ]);
      getDueRecalls(8).then(setDue).catch(() => setDue(null));
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "error",
          text:
            error instanceof Error
              ? error.message
              : "I could not read that PDF.",
        },
      ]);
    } finally {
      setWorking(false);
      textareaRef.current?.focus();
    }
  }

  return (
    <AppShell
      dueCount={due?.due_count ?? 0}
      title="New thought"
      subtitle="Crowscap is listening"
      user={user}
      context={<ChatContext memories={contextMemories} due={due} />}
    >
      <div className="conversation-scroll min-w-0 flex-1 overflow-y-auto overflow-x-hidden">
        <div className="mx-auto w-full min-w-0 max-w-[780px] px-4 pt-7 md:px-8 md:pt-10">
          {due && due.due_count > 0 ? (
            <RecallNotice
              memory={due.memories[0] ?? null}
              reminder={due.reminders[0] ?? null}
            />
          ) : null}

          <div className="mt-8 space-y-8">
            {messages.map((message) => (
              <ChatTurn
                key={message.id}
                message={message}
                onRetry={retryTextMessage}
                retryDisabled={working}
              />
            ))}
            {working ? <ThinkingTurn /> : null}
            <div ref={endRef} />
          </div>
        </div>
        <div className="h-[200px] shrink-0 md:h-[180px]" />
      </div>

      <Composer
        draft={draft}
        setDraft={setDraft}
        attachedFile={attachedFile}
        setAttachedFile={setAttachedFile}
        sendMessage={sendMessage}
        working={working}
        textareaRef={textareaRef}
      />
    </AppShell>
  );
}

function hydratePersistedMessage(message: PersistedChatMessage): ChatMessage {
  if (message.role === "user") {
    return {
      id: message.id,
      role: "user",
      text: message.content,
    };
  }

  if (!message.metadata_json) {
    return {
      id: message.id,
      role: "assistant",
      kind: "text",
      text: message.content,
    };
  }

  const metadata = normalizeChatResponse(message.metadata_json, message.content);

  if (metadata.action === "capture" && metadata.capture) {
    return {
      id: message.id,
      role: "assistant",
      kind: "capture",
      text: message.content,
      data: metadata.capture,
    };
  }

  if (
    (metadata.preference_updates?.length ?? 0) > 0 ||
    metadata.action === "answer" ||
    metadata.action === "forget" ||
    metadata.action === "self"
  ) {
    return {
      id: message.id,
      role: "assistant",
      kind: "answer",
      text: message.content,
      data: metadata,
    };
  }

  if (metadata.action === "audit" && metadata.audit) {
    return {
      id: message.id,
      role: "assistant",
      kind: "audit",
      text: message.content,
      data: metadata.audit,
    };
  }

  if (metadata.action === "reminder" && metadata.reminder) {
    return {
      id: message.id,
      role: "assistant",
      kind: "reminder",
      text: message.content,
      data: metadata,
    };
  }

  return {
    id: message.id,
    role: "assistant",
    kind: "text",
    text: message.content,
  };
}

function ChatTurn({
  message,
  onRetry,
  retryDisabled = false,
}: {
  message: ChatMessage;
  onRetry?: (text: string) => void;
  retryDisabled?: boolean;
}) {
  const [expandedUserText, setExpandedUserText] = useState(false);
  const [copied, setCopied] = useState(false);

  if (message.role === "user") {
    const isLong = message.text.length > 900 || message.text.split("\n").length > 12;
    return (
      <div className="rise-in flex justify-end">
        <div className="max-w-[92%] rounded-[18px_18px_4px_18px] bg-foreground px-4 py-3 text-[12px] font-normal leading-5 text-background md:max-w-[72%]">
          <p className={isLong && !expandedUserText ? "line-clamp-[12] whitespace-pre-wrap" : "whitespace-pre-wrap"}>
            {message.text}
          </p>
          {isLong ? (
            <button
              type="button"
              onClick={() => setExpandedUserText((current) => !current)}
              aria-expanded={expandedUserText}
              className="mt-2 text-[10px] font-semibold underline underline-offset-4 opacity-80 hover:opacity-100"
            >
              {expandedUserText ? "Show less" : "Show full text"}
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  async function copyResponse() {
    await navigator.clipboard.writeText(message.text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div className="group rise-in min-w-0">
      <div className="flex min-w-0 items-start gap-3">
        <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-foreground text-background shadow-sm">
          <BrandIcon className="size-[18px]" />
        </div>
        <div className="min-w-0 flex-1">
          <div className={message.kind === "error" ? "max-w-[620px] rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-destructive" : "max-w-[620px]"}>
            <MarkdownText
              text={message.text}
              variant="assistant"
              className="text-foreground"
            />
          </div>

          {message.kind === "capture" ? (
            <div className="mt-4">
              <MemoryReceipt data={message.data} />
            </div>
          ) : null}

          {message.kind === "answer" ? (
            <GroundedAnswer data={message.data} />
          ) : null}

          {message.kind === "audit" ? <BeliefAudit data={message.data} /> : null}

          {message.kind === "reminder" ? (
            <ReminderReceipt data={message.data} />
          ) : null}

          {message.kind === "error" ? (
            <button
              type="button"
              onClick={() => {
                if (message.retryText) onRetry?.(message.retryText);
              }}
              disabled={!message.retryText || retryDisabled}
              className="mt-2 text-[11px] font-semibold text-destructive underline decoration-destructive/30 underline-offset-4 disabled:opacity-50"
            >
              Try again
            </button>
          ) : (
            <button
              type="button"
              onClick={copyResponse}
              aria-label={copied ? "Response copied" : "Copy response"}
              className="mt-2 flex items-center gap-1 text-[10px] font-medium text-muted-foreground opacity-100 transition hover:text-foreground md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
            >
              {copied ? <CheckCheck size={12} /> : <Clipboard size={12} />}
              {copied ? "Copied" : "Copy"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ReminderReceipt({ data }: { data: ChatResponse }) {
  if (!data.reminder) return null;

  return (
    <div className="mt-4 space-y-3">
      <div className="rounded-lg border border-[#d7e5dc] bg-[#f1f7f4] px-4 py-3 text-[#2d7058]">
        <div className="flex items-center gap-2">
          <Clock3 size={14} />
          <p className="text-[9px] font-extrabold uppercase">
            Reminder scheduled
          </p>
        </div>
        <p className="mt-2 text-[12px] font-semibold leading-relaxed text-[#3f5d51]">
          {data.reminder.content}
        </p>
        <p className="mt-2 text-[10px] font-bold text-[#668074]">
          Due {formatFriendlyDateTime(data.reminder.due_at)} -{" "}
          {data.reminder.save_as_memory
            ? "also saved to memory"
            : "not saved to memory"}
        </p>
      </div>
      {data.capture ? <MemoryReceipt data={data.capture} /> : null}
    </div>
  );
}

function MemoryReceipt({ data }: { data: CaptureResponse }) {
  const [expanded, setExpanded] = useState(false);
  const [view, setView] = useState<"memories" | "original">("memories");
  const reference = parseReferenceContent(data.original_content);
  const contentLabel = sourceContentLabel(data.source_type, data.original_content);
  const displayContent = data.source_type.toLowerCase().includes("youtube") && data.original_content
    ? formatTranscriptForDisplay(data.original_content)
    : data.original_content;
  const countLabel = `${data.memories.length} ${data.memories.length === 1 ? "memory" : "memories"}`;

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-muted/40">
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-muted/60"
      >
        <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Check size={14} strokeWidth={2.4} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <p className="text-[11px] font-bold text-foreground">Saved to memory</p>
            <span className="rounded-full border border-border bg-background px-2 py-0.5 text-[9px] font-semibold text-muted-foreground">
              {sourceTypeLabel(data.source_type)}
            </span>
          </div>
          {data.source_title ? <p className="mt-1 truncate text-[11px] font-medium text-foreground">{data.source_title}</p> : null}
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-muted-foreground">
            <span>{countLabel}</span>
            {data.inferred_intents.map((intent) => (
              <span key={intent} className="rounded-full bg-background px-2 py-0.5 font-medium">{humanizeIntent(intent)}</span>
            ))}
          </div>
        </div>
        <ChevronRight
          size={15}
          className={`ml-auto text-[#73777a] transition ${
            expanded ? "rotate-90" : ""
          }`}
        />
      </button>
      {expanded ? (
        <div className="border-t border-border bg-background p-3">
          <div role="tablist" aria-label="Memory receipt views" className="mb-3 inline-flex rounded-md bg-muted p-0.5">
            <button
              type="button"
              role="tab"
              aria-selected={view === "memories"}
              onClick={() => setView("memories")}
              className={`rounded px-3 py-1.5 text-[10px] font-semibold transition ${
                view === "memories" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
              }`}
            >
              Memories
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={view === "original"}
              onClick={() => setView("original")}
              className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-[10px] font-semibold transition ${
                view === "original" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
              }`}
            >
              <FileText size={12} />
              {contentLabel}
            </button>
          </div>
          {view === "memories" ? (
            <div className="grid gap-2">
              {data.memories.map((memory) => (
                <MemoryCardView key={memory.id} memory={memory} compact />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-muted/30 p-4">
              <p className="text-[9px] font-bold uppercase tracking-wide text-muted-foreground">{contentLabel}</p>
              {reference ? (
                <dl className="mt-3 flex flex-col gap-3 text-[12px]">
                  {reference.title ? <ReferenceRow label="Title" value={reference.title} /> : null}
                  {reference.description ? <ReferenceRow label="About" value={reference.description} /> : null}
                  {reference.reason ? <ReferenceRow label="Why you saved it" value={reference.reason} /> : null}
                  {reference.link ? (
                    <div>
                      <dt className="text-[9px] font-bold uppercase tracking-wide text-muted-foreground">Link</dt>
                      <dd className="mt-1 break-all"><a href={reference.link} target="_blank" rel="noopener noreferrer" className="font-medium underline decoration-border underline-offset-4 hover:decoration-foreground">Open source</a></dd>
                    </div>
                  ) : null}
                </dl>
              ) : displayContent ? (
                <div className="mt-3 max-h-[420px] overflow-y-auto overscroll-contain pr-2">
                  <MarkdownText text={displayContent} variant="source" className="text-foreground" />
                </div>
              ) : (
                <p className="mt-3 text-[11px] font-normal leading-relaxed text-muted-foreground">
                  This older capture does not have its original text stored yet. Save the source again to restore it.
                </p>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function ReferenceRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[9px] font-bold uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap font-normal leading-5 text-foreground">{value}</dd>
    </div>
  );
}

function GroundedAnswer({ data }: { data: ChatResponse }) {
  const [showEvidence, setShowEvidence] = useState(false);

  return (
    <div className="mt-5 space-y-3">
      {data.preference_updates.length > 0 ? (
        <InsightBlock
          icon={SlidersHorizontal}
          label="Preference learned"
          items={data.preference_updates}
          tone="green"
        />
      ) : null}
      {data.knowledge_gaps.length > 0 ? (
        <InsightBlock
          icon={CircleAlert}
          label="What is still missing"
          items={data.knowledge_gaps}
          tone="amber"
        />
      ) : null}
      {data.tensions.length > 0 ? (
        <InsightBlock
          icon={GitCompareArrows}
          label="Ideas worth comparing"
          items={data.tensions.map(humanizeRelationshipText)}
          tone="rose"
        />
      ) : null}
      {data.next_step ? (
        <div className="rounded-lg border border-[#d7e5dc] bg-[#f1f7f4] px-4 py-3">
          <p className="text-[9px] font-extrabold uppercase text-[#2d7058]">
            Useful next move
          </p>
          <MarkdownText
            text={data.next_step}
            className="mt-1 text-[11px] font-semibold leading-relaxed text-[#3f5d51]"
            compact
          />
        </div>
      ) : null}
      {data.evidence.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-[#e0e2e3]">
          <button
            type="button"
            onClick={() => setShowEvidence((current) => !current)}
            className="flex w-full items-center px-4 py-3 text-left"
          >
            <span className="text-[10px] font-extrabold">
              {data.evidence.length} memories informed this answer
            </span>
            <ChevronRight
              size={14}
              className={`ml-auto transition ${showEvidence ? "rotate-90" : ""}`}
            />
          </button>
          {showEvidence ? (
            <div className="grid gap-2 border-t border-[#e6e8e9] bg-[#fafafa] p-3">
              {data.evidence.slice(0, 4).map((result) => (
                <MemoryCardView
                  key={result.memory_id}
                  memory={result}
                  compact
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function BeliefAudit({ data }: { data: BeliefAuditResponse }) {
  const [showSaved, setShowSaved] = useState(false);

  return (
    <div className="mt-5 space-y-3">
      <div className="rounded-lg border border-[#dfe2e3] bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[9px] font-extrabold uppercase text-[#6f7376]">
            Evidence audit
          </p>
          <span className="rounded-full bg-[#f0f1f2] px-2 py-1 text-[9px] font-bold text-[#55585b]">
            {data.confidence} confidence
          </span>
        </div>
        <h3 className="mt-2 text-[16px] font-[760] leading-tight text-[#111111]">
          {data.topic}
        </h3>
        <MarkdownText
          text={data.current_understanding}
          className="mt-3 text-[12px] font-semibold leading-6 text-[#3e4143]"
        />
        <MarkdownText
          text={data.confidence_reason}
          className="mt-3 rounded-md bg-[#f6f7f7] px-3 py-2 text-[11px] font-semibold leading-relaxed text-[#5f6366]"
        />
      </div>

      {data.strongest_saved_ideas.length > 0 ? (
        <InsightBlock
          icon={BadgeCheck}
          label="Strongest saved ideas"
          items={data.strongest_saved_ideas}
          tone="green"
        />
      ) : null}

      <div className="rounded-lg border border-[#d8e2eb] bg-[#f2f7fb] px-4 py-3 text-[#315872]">
        <div className="flex items-center gap-2">
          <Search size={14} />
          <p className="text-[9px] font-extrabold uppercase">
            Public source leads
          </p>
        </div>
        <MarkdownText
          text={data.public_evidence_summary}
          className="mt-2 text-[11px] font-semibold leading-relaxed"
        />
        {data.public_search_message ? (
          <p className="mt-2 text-[10px] font-bold text-[#6f7d86]">
            {data.public_search_message}
          </p>
        ) : null}
        {data.public_evidence.length > 0 ? (
          <div className="mt-3 grid gap-2">
            {data.public_evidence.slice(0, 4).map((result) => (
              <a
                key={result.url}
                href={result.url}
                target="_blank"
                rel="noreferrer"
                className="rounded-md border border-[#c9d8e4] bg-white px-3 py-2 transition hover:border-[#91aec3]"
              >
                <p className="line-clamp-2 text-[11px] font-extrabold text-[#203b4e]">
                  {result.title}
                </p>
                {result.snippet ? (
                  <p className="mt-1 line-clamp-2 text-[10px] font-semibold leading-relaxed text-[#607789]">
                    {result.snippet}
                  </p>
                ) : null}
                <p className="mt-2 truncate text-[9px] font-bold uppercase text-[#7c8d98]">
                  {result.source ?? "source"}
                </p>
              </a>
            ))}
          </div>
        ) : null}
      </div>

      {data.unsupported_or_weak_points.length > 0 ? (
        <InsightBlock
          icon={CircleAlert}
          label="Needs stronger evidence"
          items={data.unsupported_or_weak_points}
          tone="amber"
        />
      ) : null}

      {data.ideas_to_compare.length > 0 ? (
        <InsightBlock
          icon={GitCompareArrows}
          label="Ideas to compare"
          items={data.ideas_to_compare.map(humanizeRelationshipText)}
          tone="rose"
        />
      ) : null}

      {data.next_questions.length > 0 ? (
        <div className="rounded-lg border border-[#d7e5dc] bg-[#f1f7f4] px-4 py-3">
          <p className="text-[9px] font-extrabold uppercase text-[#2d7058]">
            Better questions to ask next
          </p>
          <ul className="mt-2 space-y-1.5">
            {data.next_questions.map((question) => (
              <li
                key={question}
                className="text-[11px] font-semibold leading-relaxed text-[#3f5d51]"
              >
                {question}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {data.memories.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-[#e0e2e3]">
          <button
            type="button"
            onClick={() => setShowSaved((current) => !current)}
            className="flex w-full items-center px-4 py-3 text-left"
          >
            <span className="text-[10px] font-extrabold">
              {data.memories.length} saved memories audited
            </span>
            <ChevronRight
              size={14}
              className={`ml-auto transition ${showSaved ? "rotate-90" : ""}`}
            />
          </button>
          {showSaved ? (
            <div className="grid gap-2 border-t border-[#e6e8e9] bg-[#fafafa] p-3">
              {data.memories.slice(0, 5).map((result) => (
                <MemoryCardView
                  key={result.memory_id}
                  memory={result}
                  compact
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function InsightBlock({
  icon: Icon,
  label,
  items,
  tone,
}: {
  icon: LucideIcon;
  label: string;
  items: string[];
  tone: "amber" | "rose" | "green";
}) {
  const styles = {
    amber: "border-[#eadbbd] bg-[#fcf6ea] text-[#85571e]",
    rose: "border-[#ead3d5] bg-[#fbf1f2] text-[#88464b]",
    green: "border-[#d7e5dc] bg-[#f1f7f4] text-[#2d7058]",
  }[tone];

  return (
    <div className={`rounded-lg border px-4 py-3 ${styles}`}>
      <div className="flex items-center gap-2">
        <Icon size={14} />
        <p className="text-[9px] font-extrabold uppercase">{label}</p>
      </div>
      <ul className="mt-2 space-y-1.5">
        {items.map((item) => (
          <li key={item} className="text-[11px] font-semibold leading-relaxed">
            <MarkdownText text={item} compact />
          </li>
        ))}
      </ul>
    </div>
  );
}

function RecallNotice({
  memory,
  reminder,
}: {
  memory: DueRecallsResponse["memories"][number] | null;
  reminder: DueReminder | null;
}) {
  const href = memory ? `/recall/${memory.memory_id}` : "/recall";
  const title = memory
    ? "A thought is ready to revisit"
    : "A reminder is ready";
  const body = memory
    ? memory.summary ?? memory.content
    : reminder?.content ?? "Open your recall queue";

  return (
    <Link
      href={href}
      className="fade-in flex items-center gap-3 rounded-lg border border-[#d7e5dc] bg-[#f1f7f4] px-4 py-3 transition hover:border-[#b9d2c3]"
    >
      <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-white text-[#2d7058] shadow-sm">
        {memory ? <BookOpenCheck size={17} /> : <Clock3 size={17} />}
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-extrabold text-[#245e4b]">
          {title}
        </p>
        <p className="truncate text-[11px] font-medium text-[#668074]">
          {body}
        </p>
      </div>
      <div className="ml-auto flex items-center gap-1 text-[10px] font-bold text-[#2d7058]">
        Open
        <ChevronRight size={14} />
      </div>
    </Link>
  );
}

function ThinkingTurn() {
  return (
    <div className="flex items-center gap-3 text-[#6f7376]">
      <div className="flex size-7 items-center justify-center rounded-md bg-[#09090b] text-white shadow-sm">
        <BrandIcon className="size-[18px]" />
      </div>
      <div className="flex gap-1">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="thinking-dot size-1.5 rounded-full bg-[#777b7e]"
          />
        ))}
      </div>
    </div>
  );
}

function Composer({
  draft,
  setDraft,
  attachedFile,
  setAttachedFile,
  sendMessage,
  working,
  textareaRef,
}: {
  draft: string;
  setDraft: (value: string) => void;
  attachedFile: File | null;
  setAttachedFile: (file: File | null) => void;
  sendMessage: () => void;
  working: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="absolute inset-x-0 bottom-[72px] z-30 max-w-full bg-gradient-to-t from-white via-white to-transparent px-3 pb-3 pt-8 md:bottom-0 md:px-7 md:pb-5">
      <div className="mx-auto max-w-[780px]">
        {attachedFile && (
          <div className="mb-2 flex w-max max-w-full items-center justify-between gap-3 rounded-md bg-[#f0f1f2] px-3 py-1.5 text-[12px] font-medium text-[#4f5552] shadow-sm">
            <div className="flex min-w-0 items-center gap-2">
              <FileText size={14} className="shrink-0" />
              <span className="truncate">{attachedFile.name}</span>
            </div>
            <button
              type="button"
              onClick={() => setAttachedFile(null)}
              className="shrink-0 text-[#8b8e91] transition hover:text-[#111111]"
            >
              <X size={14} />
            </button>
          </div>
        )}
        <div className="rounded-lg border border-[#cfd2d4] bg-white p-2 shadow-[0_16px_50px_rgba(17,17,17,0.12)] focus-within:border-[#92979a]">
          <textarea
            ref={textareaRef}
            value={draft}
            rows={1}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Share a thought, or ask your memory..."
            className="max-h-32 min-h-11 w-full resize-none bg-transparent px-2 py-2 text-[13px] font-medium leading-relaxed outline-none placeholder:text-[#979a9d]"
          />
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Attach a PDF"
              title="Attach a PDF"
              onClick={() => fileInputRef.current?.click()}
              disabled={working}
              className="flex size-8 items-center justify-center rounded-md text-[#6e7275] transition hover:bg-[#f0f1f2]"
            >
              <Paperclip size={17} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (file) {
                  setAttachedFile(file);
                }
              }}
            />
            <button
              type="button"
              aria-label="Add a link"
              title="Add a link"
              className="flex size-8 items-center justify-center rounded-md text-[#6e7275] transition hover:bg-[#f0f1f2]"
            >
              <Link2 size={16} />
            </button>
            <button
              type="button"
              aria-label="Send"
              onClick={sendMessage}
              disabled={(!draft.trim() && !attachedFile) || working}
              className="ml-auto flex size-8 items-center justify-center rounded-md bg-[#111111] text-white transition hover:bg-black disabled:cursor-not-allowed disabled:bg-[#d3d5d6] [&_svg]:stroke-white"
            >
              <ArrowUp size={16} strokeWidth={2.3} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatContext({
  memories,
  due,
}: {
  memories: Array<
    CaptureResponse["memories"][number] | SearchResponse["results"][number]
  >;
  due: DueRecallsResponse | null;
}) {
  const dueMemory = due?.memories[0] ?? null;
  const dueReminder = due?.reminders[0] ?? null;
  const dueHref = dueMemory ? `/recall/${dueMemory.memory_id}` : "/recall";
  const dueText = dueMemory?.content ?? dueReminder?.content;

  return (
    <div className="flex h-full flex-col overflow-y-auto px-5 py-6">
      <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
        Active context
      </p>
      <h2 className="mt-2 text-[18px] font-[750] leading-tight">
        What Crowscap is holding nearby.
      </h2>

      <div className="mt-5 space-y-2">
        {memories.length > 0 ? (
          memories.map((memory) => {
            const id = "id" in memory ? memory.id : memory.memory_id;
            return <MemoryCardView key={id} memory={memory} compact />;
          })
        ) : (
          <div className="border-y border-[#e4e5e6] py-5">
            <Search className="text-[#8b8e91]" size={17} />
            <p className="mt-3 text-[11px] font-semibold leading-relaxed text-[#74777a]">
              Related memories will gather here as the conversation develops.
            </p>
          </div>
        )}
      </div>

      {due && due.due_count > 0 ? (
        <Link
          href={dueHref}
          className="mt-auto border-t border-[#e1e3e4] pt-4"
        >
          <p className="text-[10px] font-extrabold uppercase text-[#2d7058]">
            Ready for recall
          </p>
          <p className="mt-2 line-clamp-3 text-[11px] font-semibold leading-relaxed text-[#4f5552]">
            {dueText}
          </p>
        </Link>
      ) : null}
    </div>
  );
}
