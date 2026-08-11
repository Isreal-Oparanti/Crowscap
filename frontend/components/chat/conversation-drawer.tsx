"use client";

import {
  MessageCircle,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import { SignOutButton } from "@/components/auth/sign-out-button";
import type { AppShellUser } from "@/components/shell/app-shell";
import {
  deleteConversation,
  getConversations,
} from "@/lib/api";
import type { ConversationResponse } from "@/lib/types";

export function ConversationDrawer({
  isOpen,
  onClose,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  user,
}: {
  isOpen: boolean;
  onClose: () => void;
  currentConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
  user: AppShellUser;
}) {
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      void fetchList();
    }
  }, [isOpen]);

  async function fetchList() {
    setLoading(true);
    try {
      const data = await getConversations(50);
      setConversations(data);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string, title: string) {
    if (typeof window !== "undefined" && !window.confirm(`Delete conversation "${title || "this chat"}"?`)) {
      return;
    }
    setDeletingId(id);
    try {
      await deleteConversation(id);
      setConversations((current) => current.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        onNewConversation();
      }
    } catch {
      alert("Could not delete conversation.");
    } finally {
      setDeletingId(null);
    }
  }

  function formatTime(iso: string) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const now = new Date();
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  }

  if (!isOpen) return null;

  const displayName = user.name ?? user.email?.split("@")[0] ?? "Crowscap user";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Content */}
      <aside className="relative flex w-full max-w-[320px] flex-col border-r border-[#e0e2e4] bg-white px-4 py-5 shadow-2xl rise-in">
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2">
            <MessageCircle size={20} className="text-[#2d7058]" />
            <span className="text-[15px] font-[750] text-[#111111]">
              Conversations
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close drawer"
            className="flex size-8 items-center justify-center rounded-full text-[#676a6d] hover:bg-[#f1f2f3]"
          >
            <X size={18} />
          </button>
        </div>

        <button
          type="button"
          onClick={() => {
            onNewConversation();
            onClose();
          }}
          className="mt-5 flex h-11 items-center justify-center gap-2 rounded-lg bg-[#2d7058] px-4 text-[13px] font-bold text-white transition hover:bg-[#245b47]"
        >
          <Plus size={18} />
          New Conversation
        </button>

        <p className="mt-6 px-2 text-[10px] font-extrabold uppercase tracking-wider text-[#85888b]">
          Chat History
        </p>

        <div className="mt-2 min-h-0 flex-1 overflow-y-auto space-y-1 pr-1">
          {loading && conversations.length === 0 ? (
            <p className="px-2 py-4 text-[12px] font-medium text-[#777a7e]">
              Loading conversations...
            </p>
          ) : conversations.length === 0 ? (
            <p className="px-2 py-4 text-[12px] font-medium text-[#777a7e]">
              No previous conversations found.
            </p>
          ) : (
            conversations.map((item) => {
              const isActive = item.id === currentConversationId;
              const isDeleting = item.id === deletingId;

              return (
                <div
                  key={item.id}
                  onClick={() => {
                    onSelectConversation(item.id);
                    onClose();
                  }}
                  className={`group flex cursor-pointer items-center justify-between rounded-lg px-3 py-2.5 transition ${
                    isActive
                      ? "bg-[#eaf3ee] text-[#111111]"
                      : "hover:bg-[#f5f6f7] text-[#45484b]"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <p
                      className={`truncate text-[12px] ${
                        isActive ? "font-extrabold text-[#2d7058]" : "font-semibold"
                      }`}
                    >
                      {item.title || "Untitled Chat"}
                    </p>
                    {item.updated_at ? (
                      <p className="mt-0.5 text-[10px] text-[#85888b]">
                        {formatTime(item.updated_at)}
                      </p>
                    ) : null}
                  </div>

                  <button
                    type="button"
                    disabled={isDeleting}
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleDelete(item.id, item.title);
                    }}
                    className="ml-2 flex size-7 shrink-0 items-center justify-center rounded-md text-[#85888b] opacity-0 transition group-hover:opacity-100 hover:bg-white hover:text-[#9b4c51]"
                    title="Delete conversation"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Footer Profile */}
        <div className="mt-auto border-t border-[#e0e2e4] pt-4">
          <div className="flex items-center justify-between gap-3 px-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[#2d7058] text-[11px] font-extrabold text-white">
                {initials || "U"}
              </div>
              <div className="min-w-0">
                <p className="truncate text-[12px] font-bold text-[#111111]">
                  {displayName}
                </p>
                <p className="truncate text-[10px] text-[#85888b]">
                  {user.email || ""}
                </p>
              </div>
            </div>
            <SignOutButton />
          </div>
        </div>
      </aside>
    </div>
  );
}
