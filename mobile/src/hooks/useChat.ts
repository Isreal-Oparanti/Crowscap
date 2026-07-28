import { useState, useCallback } from "react";
import { sendChatMessage } from "@/api/chat";
import type { ChatResponse } from "@/types/api";

export type LocalMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; kind: "text"; text: string }
  | { id: string; role: "assistant"; kind: "capture"; text: string; data: ChatResponse["capture"] }
  | { id: string; role: "assistant"; kind: "answer"; text: string; data: ChatResponse }
  | { id: string; role: "assistant"; kind: "error"; text: string; retryText?: string };

export function useChat(userName?: string | null) {
  const firstName = userName?.split(/\s+/)[0] ?? "there";
  const [messages, setMessages] = useState<LocalMessage[]>([
    {
      id: "opening",
      role: "assistant",
      kind: "text",
      text: `Welcome back, ${firstName}. What has your attention today?`,
    },
  ]);
  const [working, setWorking] = useState(false);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || working) return;

      const userMsg: LocalMessage = { id: crypto.randomUUID(), role: "user", text };
      setMessages((prev) => [...prev, userMsg]);
      setWorking(true);

      try {
        const history = messages
          .filter((m) => !(m.role === "assistant" && m.kind === "error"))
          .slice(-12)
          .map((m) => ({ role: m.role, content: m.text }));

        const raw = await sendChatMessage({ message: text, history });

        let assistantMsg: LocalMessage;
        if (raw.action === "capture" && raw.capture) {
          assistantMsg = { id: crypto.randomUUID(), role: "assistant", kind: "capture", text: raw.message, data: raw.capture };
        } else if (["answer", "forget", "self"].includes(raw.action) || (raw.preference_updates?.length ?? 0) > 0) {
          assistantMsg = { id: crypto.randomUUID(), role: "assistant", kind: "answer", text: raw.message, data: raw };
        } else {
          assistantMsg = { id: crypto.randomUUID(), role: "assistant", kind: "text", text: raw.message };
        }

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            kind: "error",
            text: err instanceof Error ? err.message : "I could not complete that thought.",
            retryText: text,
          },
        ]);
      } finally {
        setWorking(false);
      }
    },
    [messages, working]
  );

  return { messages, working, send };
}
