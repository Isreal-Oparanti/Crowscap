"use client";

import {
  Bell,
  Check,
  ChevronRight,
  HelpCircle,
  Info,
  LogOut,
  MessageCircle,
  RefreshCw,
  Shield,
  Sparkles,
  User,
} from "lucide-react";
import { signOut } from "next-auth/react";
import { useEffect, useState } from "react";

import type { AppShellUser } from "@/components/shell/app-shell";
import { AppShell } from "@/components/shell/app-shell";
import { getPreferences, learnPreferencesNow } from "@/lib/api";
import type { UserPreferenceProfile } from "@/lib/types";

export function SettingsWorkspace({ user }: { user: AppShellUser }) {
  const [preferences, setPreferences] = useState<UserPreferenceProfile | null>(null);
  const [loadingPref, setLoadingPref] = useState(true);
  const [learning, setLearning] = useState(false);
  const [learnMessage, setLearnMessage] = useState<string | null>(null);

  const displayName = user.name ?? user.email?.split("@")[0] ?? "Crowscap user";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  useEffect(() => {
    getPreferences()
      .then(setPreferences)
      .catch(() => undefined)
      .finally(() => setLoadingPref(false));
  }, []);

  async function handleLearnNow() {
    setLearning(true);
    setLearnMessage(null);
    try {
      const res = await learnPreferencesNow();
      setLearnMessage(
        res.updates.length > 0
          ? `Learned ${res.updates.length} pattern(s) from your context!`
          : "Preferences are already up to date.",
      );
    } catch {
      setLearnMessage("Could not update preferences.");
    } finally {
      setLearning(false);
    }
  }

  return (
    <AppShell
      title="Settings"
      subtitle="Account preferences & profile"
      user={user}
    >
      <div className="min-w-0 flex-1 overflow-y-auto px-4 py-8 md:px-8">
        <div className="mx-auto max-w-[640px] space-y-6">
          {/* Profile Card */}
          <div className="flex items-center gap-4 rounded-2xl border border-[#e2e4e5] bg-[#fafafa] p-5 shadow-xs">
            {user.image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.image}
                alt=""
                className="size-14 rounded-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-[#dfe7e3] text-[16px] font-extrabold text-[#275d4b]">
                {initials || "C"}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h2 className="truncate text-[16px] font-extrabold text-[#111111]">
                {displayName}
              </h2>
              <p className="truncate text-[12px] font-medium text-[#787c80]">
                {user.email ?? "Private account"}
              </p>
            </div>
          </div>

          {/* Notifications Section */}
          <div className="space-y-2">
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#8a8d90]">
              Notifications & Preferences
            </p>
            <div className="rounded-xl border border-[#e2e4e5] bg-white px-4 py-1 shadow-xs">
              <div className="flex items-center justify-between py-3.5">
                <div className="flex items-center gap-3">
                  <Bell size={16} className="text-[#4d5154]" />
                  <span className="text-[13px] font-semibold text-[#111111]">
                    Notification schedule
                  </span>
                </div>
                <div className="rounded-md bg-[#f2f3f4] px-2.5 py-1 text-[11px] font-bold text-[#4d5154]">
                  {preferences?.preferred_review_time || "09:00 AM"}
                </div>
              </div>
            </div>
          </div>

          {/* Memory Agent Adaptation */}
          <div className="space-y-2">
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#8a8d90]">
              Memory Agent Adaptation
            </p>
            <div className="divide-y divide-[#e8eaec] rounded-xl border border-[#e2e4e5] bg-white px-4 shadow-xs">
              <div className="flex items-center justify-between py-3.5">
                <div className="flex items-center gap-3">
                  <MessageCircle size={16} className="text-[#4d5154]" />
                  <span className="text-[13px] font-semibold text-[#111111]">
                    Answer style
                  </span>
                </div>
                <div className="rounded-md bg-[#f2f3f4] px-2.5 py-1 text-[11px] font-bold capitalize text-[#4d5154]">
                  {preferences?.answer_style || "Concise"}
                </div>
              </div>

              <div className="flex items-center justify-between py-3.5">
                <div className="flex items-center gap-3">
                  <Shield size={16} className="text-[#4d5154]" />
                  <span className="text-[13px] font-semibold text-[#111111]">
                    Evidence strictness
                  </span>
                </div>
                <div className="rounded-md bg-[#f2f3f4] px-2.5 py-1 text-[11px] font-bold capitalize text-[#4d5154]">
                  {preferences?.evidence_strictness || "Balanced"}
                </div>
              </div>

              <div className="flex items-center justify-between py-3.5">
                <div className="flex items-center gap-3">
                  <HelpCircle size={16} className="text-[#4d5154]" />
                  <span className="text-[13px] font-semibold text-[#111111]">
                    Challenge style
                  </span>
                </div>
                <div className="rounded-md bg-[#f2f3f4] px-2.5 py-1 text-[11px] font-bold capitalize text-[#4d5154]">
                  {preferences?.challenge_style || "Direct"}
                </div>
              </div>

              <div className="flex items-center justify-between py-3.5">
                <div className="flex items-center gap-3">
                  <Sparkles size={16} className="text-[#2d7058]" />
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-[#111111]">
                      Adapt agent to recent thoughts
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  disabled={learning}
                  onClick={handleLearnNow}
                  className="rounded-md bg-[#eaf3ee] px-2.5 py-1 text-[11px] font-extrabold text-[#2d7058] transition hover:bg-[#d8e9de] disabled:opacity-50"
                >
                  {learning ? "Adapting..." : "Adapt Now"}
                </button>
              </div>
            </div>
            {learnMessage ? (
              <p className="px-1 text-[11px] font-medium text-[#2d7058]">
                {learnMessage}
              </p>
            ) : null}
          </div>

          {/* Sign Out Button */}
          <button
            type="button"
            onClick={() => void signOut()}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-[#f5d0d0] bg-[#fff5f5] text-[13px] font-extrabold text-[#9b4c51] transition hover:bg-[#ffebeb]"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </AppShell>
  );
}
