"use client";

import {
  Bell,
  Feather,
  MessageCircle,
  Plus,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type AppShellProps = {
  children: ReactNode;
  context?: ReactNode;
  dueCount?: number;
  title?: string;
  subtitle?: string;
};

const navigation = [
  { href: "/", label: "Chat", icon: MessageCircle },
  { href: "/recall", label: "Recall", icon: Sparkles },
  { href: "/search", label: "Search", icon: Search },
];

export function AppShell({
  children,
  context,
  dueCount = 0,
  title = "Crowscap",
  subtitle = "Your thinking, still within reach",
}: AppShellProps) {
  const pathname = usePathname();

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
                  <span className="ml-auto min-w-5 rounded-full bg-[#111111] px-1.5 py-0.5 text-center text-[10px] text-white">
                    {dueCount}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto">
          <div className="mb-4 border-t border-[#e0e2e4] pt-4">
            <div className="flex items-center gap-3 rounded-md px-3 py-2">
              <div className="flex size-8 items-center justify-center rounded-full bg-[#dfe7e3] text-[11px] font-extrabold text-[#275d4b]">
                JO
              </div>
              <div className="min-w-0">
                <p className="truncate text-[12px] font-bold">Json O.</p>
                <p className="truncate text-[10px] text-[#85888b]">
                  Learning workspace
                </p>
              </div>
              <Settings className="ml-auto text-[#7c7f82]" size={16} />
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
          <Link
            href="/recall"
            aria-label="Open recall notifications"
            className="relative ml-auto flex size-9 items-center justify-center rounded-full text-[#44474a] transition hover:bg-[#f1f2f3]"
          >
            <Bell size={18} strokeWidth={1.8} />
            {dueCount > 0 ? (
              <span className="absolute right-0.5 top-0.5 size-2 rounded-full border-2 border-white bg-[#2d7058]" />
            ) : null}
          </Link>
        </header>
        {children}
        <MobileNavigation pathname={pathname} dueCount={dueCount} />
      </main>

      <aside className="context-rail desktop-rail bg-[#f8f8f8]">
        {context ?? <DefaultContext />}
      </aside>
    </div>
  );
}

function BrandMark() {
  return (
    <div className="flex size-9 items-center justify-center rounded-md bg-[#111111] text-white shadow-[0_4px_16px_rgba(17,17,17,0.14)]">
      <Feather size={18} strokeWidth={2.2} />
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
              <span className="absolute right-[calc(50%-19px)] top-3 min-w-4 rounded-full bg-[#2d7058] px-1 text-center text-[9px] leading-4 text-white">
                {dueCount}
              </span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}

function DefaultContext() {
  return (
    <div className="flex h-full flex-col px-5 py-6">
      <p className="text-[10px] font-extrabold uppercase text-[#8a8d90]">
        In mind
      </p>
      <h2 className="mt-2 text-[20px] font-[750] leading-tight">
        A clearer view of what you know.
      </h2>
      <div className="mt-6 space-y-2">
        {[
          ["Distribution", "6 memories"],
          ["Product thinking", "4 memories"],
          ["Design systems", "3 memories"],
        ].map(([topic, count]) => (
          <div
            key={topic}
            className="flex items-center justify-between border-b border-[#e4e5e6] py-3"
          >
            <span className="text-[12px] font-semibold">{topic}</span>
            <span className="text-[10px] text-[#8b8e91]">{count}</span>
          </div>
        ))}
      </div>
      <div className="mt-auto border-t border-[#e1e3e4] pt-4">
        <div className="flex items-center gap-2 text-[#5d6265]">
          <Sparkles size={14} />
          <span className="text-[10px] font-bold uppercase">Memory active</span>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-[#84878a]">
          Your sources remain attached to every remembered idea.
        </p>
      </div>
    </div>
  );
}
