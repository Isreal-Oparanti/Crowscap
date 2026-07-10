"use client";

import {
  ArrowUp,
  Check,
  ChevronRight,
  CircleAlert,
  FileText,
  GitCompareArrows,
  Link2,
  Paperclip,
  Search,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { MemoryCardView } from "@/components/memory/memory-card";
import { AppShell } from "@/components/shell/app-shell";
import {
  getCurrentConversation,
  getDueRecalls,
  sendChatMessage,
  uploadPdfToChat,
} from "@/lib/api";
import { humanizeRelationshipText } from "@/lib/chat";
import type {
  BeliefAuditResponse,
  CaptureResponse,
  ChatResponse,
  ConversationTurn,
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
      kind: "error";
      text: string;
    };

const openingMessages: ChatMessage[] = [
  {
    id: "opening",
    role: "assistant",
    kind: "text",
    text: "Welcome back, Json. What has your attention today?",
  },
];

export function ChatWorkspace() {
  const [messages, setMessages] = useState<ChatMessage[]>(openingMessages);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [working, setWorking] = useState(false);
  const [due, setDue] = useState<DueRecallsResponse | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getDueRecalls(8).then(setDue).catch(() => setDue(null));
    getCurrentConversation()
      .then((conversation) => {
        if (!conversation) return;
        setConversationId(conversation.id);
        const restored = conversation.messages.map(hydratePersistedMessage);
        setMessages(restored.length > 0 ? restored : openingMessages);
      })
      .catch(() => {
        setConversationId(null);
      });
  }, []);

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
        : latestAssistant.data.evidence.slice(0, 3);
  }, [messages]);

  async function sendMessage() {
    const text = draft.trim();
    if (!text || working) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text,
    };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setWorking(true);

    try {
      const history = messages
        .map<ConversationTurn>((message) => ({
          role: message.role,
          content: message.text,
        }))
        .slice(-12);
      const response = await sendChatMessage(text, history, conversationId);
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
          : response.action === "answer"
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
        },
      ]);
    } finally {
      setWorking(false);
      textareaRef.current?.focus();
    }
  }

  async function uploadPdf(file: File) {
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
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: `Uploaded PDF: ${file.name}`,
    };
    setMessages((current) => [...current, userMessage]);
    setWorking(true);

    try {
      const response = await uploadPdfToChat(file, conversationId);
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
      context={<ChatContext memories={contextMemories} due={due} />}
    >
      <div className="conversation-scroll min-w-0 flex-1 overflow-y-auto overflow-x-hidden">
        <div className="mx-auto w-full min-w-0 max-w-[780px] px-4 pb-40 pt-7 md:px-8 md:pt-10">
          {due && due.due_count > 0 ? (
            <RecallNotice recall={due.memories[0]} count={due.due_count} />
          ) : null}

          <div className="mt-8 space-y-8">
            {messages.map((message) => (
              <ChatTurn key={message.id} message={message} />
            ))}
            {working ? <ThinkingTurn /> : null}
            <div ref={endRef} />
          </div>
        </div>
      </div>

      <Composer
        draft={draft}
        setDraft={setDraft}
        sendMessage={sendMessage}
        uploadPdf={uploadPdf}
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

  const metadata = message.metadata_json;
  if (metadata?.action === "capture" && metadata.capture) {
    return {
      id: message.id,
      role: "assistant",
      kind: "capture",
      text: message.content,
      data: metadata.capture,
    };
  }

  if (metadata?.action === "answer") {
    return {
      id: message.id,
      role: "assistant",
      kind: "answer",
      text: message.content,
      data: metadata,
    };
  }

  if (metadata?.action === "audit" && metadata.audit) {
    return {
      id: message.id,
      role: "assistant",
      kind: "audit",
      text: message.content,
      data: metadata.audit,
    };
  }

  return {
    id: message.id,
    role: "assistant",
    kind: "text",
    text: message.content,
  };
}

function ChatTurn({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="rise-in flex justify-end">
        <div className="max-w-[88%] rounded-[18px_18px_4px_18px] bg-[#111111] px-4 py-3 text-[13px] font-medium leading-relaxed text-white md:max-w-[72%]">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="rise-in min-w-0">
      <div className="flex min-w-0 items-start gap-3">
        <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-[#111111] text-white">
          <Sparkles size={14} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="max-w-[620px] break-words text-[14px] font-semibold leading-relaxed text-[#252627]">
            {message.text}
          </p>

          {message.kind === "capture" ? (
            <div className="mt-4">
              <MemoryReceipt data={message.data} />
            </div>
          ) : null}

          {message.kind === "answer" ? (
            <GroundedAnswer data={message.data} />
          ) : null}

          {message.kind === "audit" ? <BeliefAudit data={message.data} /> : null}

          {message.kind === "error" ? (
            <button
              type="button"
              className="mt-3 text-[11px] font-bold text-[#9b4c51] underline decoration-[#d8b8ba] underline-offset-4"
            >
              Try again
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function MemoryReceipt({ data }: { data: CaptureResponse }) {
  const [expanded, setExpanded] = useState(true);
  const [view, setView] = useState<"memories" | "original">("memories");

  return (
    <div className="overflow-hidden rounded-lg border border-[#dfe2e3] bg-[#f8f9f9]">
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <div className="flex size-7 items-center justify-center rounded-full bg-[#e7f2ec] text-[#2d7058]">
          <Check size={14} strokeWidth={2.4} />
        </div>
        <div>
          <p className="text-[11px] font-extrabold">Memory receipt</p>
          <p className="text-[10px] font-medium text-[#7d8083]">
            {data.memories.length} memories ·{" "}
            {data.inferred_intents.join(", ") || "saved"}
          </p>
        </div>
        <ChevronRight
          size={15}
          className={`ml-auto text-[#73777a] transition ${
            expanded ? "rotate-90" : ""
          }`}
        />
      </button>
      {expanded ? (
        <div className="border-t border-[#e5e7e8] bg-white p-3">
          <div className="mb-3 inline-flex rounded-md bg-[#f0f1f2] p-0.5">
            <button
              type="button"
              onClick={() => setView("memories")}
              className={`rounded px-3 py-1.5 text-[10px] font-extrabold transition ${
                view === "memories"
                  ? "bg-white text-[#111111] shadow-sm"
                  : "text-[#777b7e]"
              }`}
            >
              Memories
            </button>
            <button
              type="button"
              onClick={() => setView("original")}
              className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-[10px] font-extrabold transition ${
                view === "original"
                  ? "bg-white text-[#111111] shadow-sm"
                  : "text-[#777b7e]"
              }`}
            >
              <FileText size={12} />
              Original
            </button>
          </div>
          {view === "memories" ? (
            <div className="grid gap-2">
              {data.memories.map((memory) => (
                <MemoryCardView key={memory.id} memory={memory} compact />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-[#e1e3e4] bg-[#fafafa] p-4">
              <p className="text-[9px] font-extrabold uppercase text-[#85888b]">
                Exactly as saved
              </p>
              {data.original_content ? (
                <p className="mt-3 max-h-[420px] overflow-y-auto whitespace-pre-wrap break-words text-[12px] font-medium leading-6 text-[#303234]">
                  {data.original_content}
                </p>
              ) : (
                <p className="mt-3 text-[11px] font-medium leading-relaxed text-[#74777a]">
                  This older capture does not have its original text stored yet.
                  Save the same source once more to restore it.
                </p>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function GroundedAnswer({ data }: { data: ChatResponse }) {
  const [showEvidence, setShowEvidence] = useState(false);

  return (
    <div className="mt-5 space-y-3">
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
          <p className="mt-1 text-[11px] font-semibold leading-relaxed text-[#3f5d51]">
            {data.next_step}
          </p>
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
        <p className="mt-3 text-[12px] font-semibold leading-6 text-[#3e4143]">
          {data.current_understanding}
        </p>
        <p className="mt-3 rounded-md bg-[#f6f7f7] px-3 py-2 text-[11px] font-semibold leading-relaxed text-[#5f6366]">
          {data.confidence_reason}
        </p>
      </div>

      {data.strongest_saved_ideas.length > 0 ? (
        <InsightBlock
          icon={Sparkles}
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
        <p className="mt-2 text-[11px] font-semibold leading-relaxed">
          {data.public_evidence_summary}
        </p>
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
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function RecallNotice({
  recall,
  count,
}: {
  recall: DueRecallsResponse["memories"][number];
  count: number;
}) {
  return (
    <Link
      href={`/recall/${recall.memory_id}`}
      className="fade-in flex items-center gap-3 rounded-lg border border-[#d7e5dc] bg-[#f1f7f4] px-4 py-3 transition hover:border-[#b9d2c3]"
    >
      <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-white text-[#2d7058] shadow-sm">
        <Sparkles size={17} />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-extrabold text-[#245e4b]">
          A thought is ready to revisit
        </p>
        <p className="truncate text-[11px] font-medium text-[#668074]">
          {recall.summary ?? recall.content}
        </p>
      </div>
      <div className="ml-auto flex items-center gap-1 text-[10px] font-bold text-[#2d7058]">
        {count > 1 ? `+${count - 1}` : "Open"}
        <ChevronRight size={14} />
      </div>
    </Link>
  );
}

function ThinkingTurn() {
  return (
    <div className="flex items-center gap-3 text-[#6f7376]">
      <div className="flex size-7 items-center justify-center rounded-md bg-[#111111] text-white">
        <Sparkles size={14} />
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
  sendMessage,
  uploadPdf,
  working,
  textareaRef,
}: {
  draft: string;
  setDraft: (value: string) => void;
  sendMessage: () => void;
  uploadPdf: (file: File) => void;
  working: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="absolute inset-x-0 bottom-[72px] z-30 max-w-full bg-gradient-to-t from-white via-white to-transparent px-3 pb-3 pt-8 md:bottom-0 md:px-7 md:pb-5">
      <div className="mx-auto max-w-[780px]">
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
                  uploadPdf(file);
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
            <span className="ml-1 hidden items-center gap-1.5 text-[9px] font-bold uppercase text-[#8a8d90] sm:flex">
              <Sparkles size={11} />
              Auto
            </span>
            <button
              type="button"
              aria-label="Send"
              onClick={sendMessage}
              disabled={!draft.trim() || working}
              className="ml-auto flex size-8 items-center justify-center rounded-md bg-[#111111] text-white transition hover:bg-black disabled:cursor-not-allowed disabled:bg-[#d3d5d6]"
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
          href={`/recall/${due.memories[0].memory_id}`}
          className="mt-auto border-t border-[#e1e3e4] pt-4"
        >
          <p className="text-[10px] font-extrabold uppercase text-[#2d7058]">
            Ready for recall
          </p>
          <p className="mt-2 line-clamp-3 text-[11px] font-semibold leading-relaxed text-[#4f5552]">
            {due.memories[0].content}
          </p>
        </Link>
      ) : null}
    </div>
  );
}
