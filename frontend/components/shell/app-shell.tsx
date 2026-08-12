"use client";

import {
  BookOpenCheck,
  Bell,
  MessageCircle,
  PanelLeft,
  Plus,
  Search,
  Settings,
  WifiOff,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { SignOutButton } from "@/components/auth/sign-out-button";
import {
  NotificationRuntime,
} from "@/components/notifications/notification-runtime";
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
  contentMode?: "default" | "wide";
  title?: string;
  subtitle?: string;
  user: AppShellUser;
  onOpenDrawer?: () => void;
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
  contentMode = "default",
  title = "Crowscap",
  subtitle = "Your thinking, still within reach",
  user,
  onOpenDrawer,
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

  const isWide = contentMode === "wide";

  return (
    <div className={`app-grid ${isWide ? "app-grid-wide" : ""}`}>
      <aside className="desktop-rail flex flex-col bg-[#f5f6f7] px-4 py-5">
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-3">
            {onOpenDrawer ? (
              <button
                type="button"
                onClick={onOpenDrawer}
                className="flex size-9 items-center justify-center rounded-lg border border-[#e1e3e4] bg-white text-[#111111] transition hover:bg-[#e8eaec]"
                aria-label="Open conversation history drawer"
                title="Open conversation history"
              >
                <PanelLeft size={18} />
              </button>
            ) : (
              <BrandMark />
            )}
            <div>
              <p className="text-[15px] font-[750]">Crowscap</p>
              <p className="text-[11px] font-medium text-[#777a7e]">
                Personal intelligence
              </p>
            </div>
          </div>
        </div>

        <Link
          href="/"
          className="mt-6 flex h-10 items-center justify-center gap-2 rounded-md bg-[#111111] px-3 text-[13px] font-semibold text-white transition hover:bg-black"
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
            </div>
          </div>
        </div>
      </aside>

      <main className="workspace-main relative flex flex-col">
        <header className="flex h-[68px] shrink-0 items-center border-b border-[#e7e8e9] bg-white px-4 md:px-6">
          {onOpenDrawer ? (
            <button
              type="button"
              onClick={onOpenDrawer}
              className="mr-3 flex size-9 items-center justify-center rounded-full border border-[#e1e3e4] bg-[#f5f6f7] text-[#111111] transition hover:bg-[#e8eaec]"
              aria-label="Open conversation history drawer"
              title="Open conversation history"
            >
              <PanelLeft size={18} />
            </button>
          ) : (
            <div className="mr-3.5 md:hidden">
              <BrandMark />
            </div>
          )}
          <div className="min-w-0">
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
              <Link
                href="/settings"
                aria-label="Open settings"
                className="flex size-9 items-center justify-center rounded-full text-[#44474a] transition hover:bg-[#f1f2f3]"
              >
                <Settings size={18} strokeWidth={1.8} />
              </Link>
            </div>
          </div>
        </header>
        {children}
        <MobileNavigation pathname={pathname} dueCount={dueCount} />
      </main>

      {!isWide ? (
        <aside className="context-rail desktop-rail bg-[#f8f8f8]">
          {context ?? <DefaultContext />}
        </aside>
      ) : null}
      <NotificationRuntime />
    </div>
  );
}

function BrandMark() {
  return (
    <div className="flex size-10 items-center justify-center rounded-[11px] border border-[#e4e5e6] bg-white">
      <BrandIcon className="size-[28px]" />
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
        if (active) setPreferences(profile);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="h-full px-5 py-6">
      <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
        Memory system
      </p>
      <div className="mt-4 rounded-xl border border-[#e1e3e4] bg-white p-4">
        <p className="text-[12px] font-extrabold">Active orientation</p>
        <p className="mt-1 text-[11px] font-medium text-[#777b7e]">
          Crowscap continuously extracts intentions, claims, principles, and
          action items from your inputs.
        </p>
      </div>
      {preferences?.topics_of_interest?.length ? (
        <div className="mt-4 rounded-xl border border-[#e1e3e4] bg-white p-4">
          <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
            Topics of interest
          </p>
          <ul className="mt-2 space-y-2 text-[11px] font-semibold text-[#3d4043]">
            {preferences.topics_of_interest.slice(0, 3).map((topic) => (
              <li key={topic} className="line-clamp-2">
                • {topic}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
