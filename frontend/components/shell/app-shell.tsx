"use client";

import {
  BookOpenCheck,
  Bell,
  BrainCircuit,
  MessageCircle,
  Plus,
  Search,
  WifiOff,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { SignOutButton } from "@/components/auth/sign-out-button";
import { BrandIcon } from "@/components/ui/brand-icon";
import { getPreferences } from "@/lib/api";
import type { UserPreferenceProfile } from "@/lib/types";

export type AppShellUser = {
  id?: string | null;
  name?: string | null;
  email?: string | null;
  image?: string | null;
};

type AppShellProps = {
  children: ReactNode;
  context?: ReactNode;
  dueCount?: number;
  title?: string;
  subtitle?: string;
  user: AppShellUser;
};

const navigation = [
  { href: "/", label: "Chat", icon: MessageCircle },
  { href: "/recall", label: "Recall", icon: BookOpenCheck },
  { href: "/search", label: "Search", icon: Search },
];

export function AppShell({
  children,
  context,
  dueCount = 0,
  title = "Crowscap",
  subtitle = "Your thinking, still within reach",
  user,
}: AppShellProps) {
  const pathname = usePathname();
  const displayName = user.name ?? user.email?.split("@")[0] ?? "Crowscap user";
  const workspaceLabel = user.email ?? "Private workspace";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <div className="app-grid">
      <aside className="desktop-rail flex flex-col bg-[#f5f6f7] px-4 py-5">
        <div className="flex items-center gap-3 px-2">
          <BrandMark />
          <div>
            <p className="text-[15px] font-[750]">Crowscap</p>
            <p className="text-[11px] font-medium text-[#777a7e]">
              Personal intelligence
            </p>
          </div>
        </div>

        <Link
          href="/"
          className="mt-7 flex h-10 items-center justify-center gap-2 rounded-md bg-[#111111] px-3 text-[13px] font-semibold text-white transition hover:bg-black"
        >
          <Plus size={16} strokeWidth={2} />
          New thought
        </Link>

        <nav className="mt-6 space-y-1">
          {navigation.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex h-10 items-center gap-3 rounded-md px-3 text-[13px] font-semibold transition ${
                  active
                    ? "bg-white text-[#111111] shadow-[0_1px_0_rgba(0,0,0,0.04)]"
                    : "text-[#676a6d] hover:bg-white/70 hover:text-[#111111]"
                }`}
                >
                  <Icon size={17} strokeWidth={1.9} />
                  <span>{item.label}</span>
                  {item.label === "Recall" && dueCount > 0 ? (
                  <span className="ml-auto flex items-center gap-1.5 rounded-full bg-[#eaf3ee] px-2 py-1 text-[9px] font-extrabold uppercase text-[#2d7058]">
                    <span className="size-1.5 rounded-full bg-[#2d7058]" />
                    Ready
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto">
          <div className="mb-4 border-t border-[#e0e2e4] pt-4">
            <div className="flex items-center gap-3 rounded-md px-3 py-2">
              {user.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={user.image}
                  alt=""
                  className="size-8 rounded-full object-cover"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="flex size-8 items-center justify-center rounded-full bg-[#dfe7e3] text-[11px] font-extrabold text-[#275d4b]">
                  {initials || "C"}
                </div>
              )}
              <div className="min-w-0">
                <p className="truncate text-[12px] font-bold">{displayName}</p>
                <p className="truncate text-[10px] text-[#85888b]">
                  {workspaceLabel}
                </p>
              </div>
              <SignOutButton />
            </div>
          </div>
        </div>
      </aside>

      <main className="workspace-main relative flex flex-col">
        <header className="flex h-[68px] shrink-0 items-center border-b border-[#e7e8e9] bg-white px-4 md:px-6">
          <div className="md:hidden">
            <BrandMark />
          </div>
          <div className="ml-3 min-w-0 md:ml-0">
            <h1 className="truncate text-[15px] font-[750]">{title}</h1>
            <p className="truncate text-[11px] font-medium text-[#7b7e82]">
              {subtitle}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-1">
            <Link
              href="/recall"
              aria-label="Open recall notifications"
              className="relative flex size-9 items-center justify-center rounded-full text-[#44474a] transition hover:bg-[#f1f2f3]"
            >
              <Bell size={18} strokeWidth={1.8} />
              {dueCount > 0 ? (
                <span className="absolute right-0.5 top-0.5 size-2 rounded-full border-2 border-white bg-[#2d7058]" />
              ) : null}
            </Link>
            <div className="md:hidden">
              <SignOutButton className="flex size-9 items-center justify-center rounded-full text-[#44474a] transition hover:bg-[#f1f2f3]" />
            </div>
          </div>
        </header>
        {children}
        <MobileNavigation pathname={pathname} dueCount={dueCount} />
      </main>

      <aside className="context-rail desktop-rail bg-[#f8f8f8]">
        {context ?? <DefaultContext />}
      </aside>
      <NetworkToastHost />
    </div>
  );
}

function BrandMark() {
  return (
    <div className="flex size-9 items-center justify-center rounded-md bg-[#09090b] text-white shadow-[0_4px_16px_rgba(9,9,11,0.2)]">
      <BrandIcon className="size-[22px]" />
    </div>
  );
}

function MobileNavigation({
  pathname,
  dueCount,
}: {
  pathname: string;
  dueCount: number;
}) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 grid h-[72px] grid-cols-3 border-t border-[#e2e4e5] bg-white/95 px-5 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl md:hidden">
      {navigation.map((item) => {
        const active =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`relative flex flex-col items-center justify-center gap-1 text-[10px] font-bold ${
              active ? "text-[#111111]" : "text-[#888b8e]"
            }`}
          >
            <Icon size={20} strokeWidth={active ? 2.2 : 1.8} />
            <span>{item.label}</span>
            {item.label === "Recall" && dueCount > 0 ? (
              <span className="absolute right-[calc(50%-18px)] top-3 size-2.5 rounded-full border-2 border-white bg-[#2d7058]" />
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}

function DefaultContext() {
  const [preferences, setPreferences] = useState<UserPreferenceProfile | null>(
    null,
  );

  useEffect(() => {
    let active = true;
    getPreferences()
      .then((profile) => {
        if (active) {
          setPreferences(profile);
        }
      })
      .catch(() => {
        if (active) {
          setPreferences(null);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const topics = [
    ...(preferences?.topics_of_interest ?? []),
    ...(preferences?.inferred_topics ?? []),
  ].filter((topic, index, list) => list.indexOf(topic) === index);
  const signals = preferences?.learning_signals ?? [];

  return (
    <div className="flex h-full flex-col px-5 py-6">
      <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
        Crowscap is learning
      </p>
      <h2 className="mt-2 text-[20px] font-[750] leading-tight">
        Your memory should get more personal over time.
      </h2>
      <div className="mt-6 space-y-2">
        <PreferenceRow
          label="Answers"
          value={preferences?.answer_style ?? "balanced"}
        />
        <PreferenceRow
          label="Evidence"
          value={preferences?.evidence_strictness ?? "balanced"}
        />
        <PreferenceRow
          label="Challenge"
          value={preferences?.challenge_style ?? "balanced"}
        />
      </div>
      {topics.length > 0 ? (
        <div className="mt-6">
          <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
            Topics it has noticed
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {topics.slice(0, 8).map((topic) => (
              <span
                key={topic}
                className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-[#424548] shadow-[0_0_0_1px_#e2e4e5]"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {signals.length > 0 ? (
        <div className="mt-6 rounded-md border border-[#d7e9df] bg-[#eff8f3] p-3 text-[#285b48]">
          <p className="text-[10px] font-extrabold uppercase">
            Latest learning signal
          </p>
          <p className="mt-2 text-[11px] leading-relaxed">{signals[0]}</p>
        </div>
      ) : null}
      <div className="mt-auto border-t border-[#e1e3e4] pt-4">
        <div className="flex items-center gap-2 text-[#5d6265]">
          <BrainCircuit size={14} />
          <span className="text-[10px] font-bold uppercase">Agent memory</span>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-[#84878a]">
          Explicit preferences are treated as strongest. Inferred preferences
          are lower-confidence and can change as you use Crowscap.
        </p>
      </div>
    </div>
  );
}

function PreferenceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-[#e4e5e6] py-3">
      <span className="text-[12px] font-semibold">{label}</span>
      <span className="rounded-full bg-white px-2 py-1 text-[10px] font-bold uppercase text-[#676a6d] shadow-[0_0_0_1px_#e4e5e6]">
        {value}
      </span>
    </div>
  );
}

function NetworkToastHost() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const onIssue = (event: Event) => {
      const detail = (event as CustomEvent<{ message?: string }>).detail;
      const nextMessage =
        typeof detail?.message === "string" && detail.message.trim()
          ? detail.message
          : "Crowscap could not reach the memory service. Try again in a moment.";
      setMessage(nextMessage);
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => setMessage(null), 5200);
    };

    window.addEventListener("crowscap:api-issue", onIssue);
    return () => {
      window.removeEventListener("crowscap:api-issue", onIssue);
      if (timeout) clearTimeout(timeout);
    };
  }, []);

  if (!message) return null;

  return (
    <div className="fixed bottom-5 left-1/2 z-50 w-[min(92vw,420px)] -translate-x-1/2 md:bottom-6 md:left-auto md:right-6 md:translate-x-0">
      <div className="flex items-start gap-3 rounded-lg border border-[#ded4bf] bg-[#fffaf0] px-4 py-3 text-[#6f5421] shadow-[0_18px_60px_rgba(0,0,0,0.14)]">
        <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-[#f5ead3]">
          <WifiOff size={15} strokeWidth={2.1} />
        </div>
        <div>
          <p className="text-[11px] font-extrabold uppercase">Connection issue</p>
          <p className="mt-1 text-[12px] font-semibold leading-relaxed">
            {message}
          </p>
        </div>
      </div>
    </div>
  );
}
