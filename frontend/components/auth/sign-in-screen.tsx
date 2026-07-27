"use client";

import {
  ArrowRight,
  Bell,
  BookOpenCheck,
  Check,
  FileText,
  LockKeyhole,
  Search,
} from "lucide-react";
import { signIn } from "next-auth/react";
import type { ReactNode } from "react";
import { useState } from "react";

import { InstallBanner } from "@/components/pwa/install-banner";
import { BrandIcon } from "@/components/ui/brand-icon";

const proofRows = [
  "Saves the reason, not just the link.",
  "Finds meaning across notes, videos, PDFs, and chats.",
  "Brings one useful thing back when it can help.",
];

const capabilityCards = [
  {
    icon: <FileText size={15} />,
    title: "Capture",
    body: "Drop in links, notes, videos, PDFs, and ideas without building folders first.",
  },
  {
    icon: <Search size={15} />,
    title: "Ask",
    body: "Search by meaning and compare what your sources say, even months later.",
  },
  {
    icon: <Bell size={15} />,
    title: "Return",
    body: "Get reminded of the right memory when it can change what you do next.",
  },
];

export function SignInScreen() {
  const [signingInProvider, setSigningInProvider] = useState<
    "google" | "demo" | null
  >(null);

  function handleGoogleSignIn() {
    setSigningInProvider("google");
    void signIn("google", { callbackUrl: "/" }).finally(() => {
      setSigningInProvider(null);
    });
  }

  async function handleDemoSignIn() {
    setSigningInProvider("demo");
    const res = await signIn("credentials", {
      email: "yc@crowscap.xyz",
      password: "demo2026",
      redirect: false,
      callbackUrl: "/",
    });
    if (res?.url) {
      window.location.href = res.url;
    } else {
      setSigningInProvider(null);
      window.location.reload();
    }
  }

  return (
    <main className="min-h-screen bg-[#f5f5f3] text-[#101112]">
      <section className="relative flex min-h-screen flex-col overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-px bg-[#d7d9da]" />
        <div className="absolute inset-y-0 left-1/2 hidden w-px bg-[#e4e5e5] lg:block" />

        <header className="mx-auto flex w-full max-w-[1220px] items-center justify-between px-5 py-5 md:px-8">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-[12px] border border-[#dedfdf] bg-white shadow-[0_12px_34px_rgba(17,17,17,0.12)]">
              <BrandIcon className="size-8" />
            </div>
            <div>
              <p className="text-[17px] font-[850] tracking-[-0.02em]">
                Crowscap
              </p>
              <p className="text-[12px] font-semibold text-[#6f7376]">
                Personal intelligence
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-[#dedfdf] bg-white px-3 py-1.5 text-[11px] font-extrabold text-[#4d5154] shadow-sm sm:flex">
            <LockKeyhole size={13} />
            Private by default
          </div>
        </header>

        <div className="mx-auto grid w-full max-w-[1220px] flex-1 items-center gap-10 px-5 pb-28 pt-8 md:px-8 lg:grid-cols-[minmax(0,0.92fr)_minmax(430px,0.8fr)] lg:gap-16 lg:pb-24 lg:pt-2">
          <div className="max-w-[760px]">
            <p className="inline-flex items-center gap-2 rounded-full border border-[#dedfdf] bg-white px-3 py-1.5 text-[11px] font-extrabold uppercase tracking-[0.12em] text-[#3f4447] shadow-sm">
              <BookOpenCheck size={13} />
              Memory that acts with you
            </p>
            <h1 className="mt-6 text-[48px] font-[880] leading-[0.95] tracking-[-0.058em] md:text-[76px] lg:text-[92px]">
              Save what you learn. Ask it later.
            </h1>
            <p className="mt-7 max-w-[680px] text-[17px] font-medium leading-8 text-[#464a4d] md:text-[19px]">
              Crowscap is a private memory layer for people who learn from
              scattered sources and need those ideas to return at the right
              moment.
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:max-w-[430px]">
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={signingInProvider !== null}
                className="group inline-flex h-12 items-center justify-between rounded-[10px] border border-[#d5d8da] bg-white px-4 text-[13px] font-extrabold text-[#111111] shadow-[0_16px_44px_rgba(17,17,17,0.10)] transition hover:border-[#a8adb0] hover:bg-[#fbfbfb] disabled:cursor-wait disabled:opacity-70"
              >
                <span className="inline-flex items-center gap-3">
                  <GoogleMark />
                  {signingInProvider === "google"
                    ? "Opening Google..."
                    : "Continue with Google"}
                </span>
                <ArrowRight
                  size={16}
                  className="transition group-hover:translate-x-0.5"
                />
              </button>
              <button
                type="button"
                onClick={handleDemoSignIn}
                disabled={signingInProvider !== null}
                className="inline-flex h-12 items-center justify-center rounded-[10px] bg-[#111111] px-4 text-[13px] font-extrabold text-white shadow-[0_16px_44px_rgba(17,17,17,0.16)] transition hover:bg-black disabled:cursor-wait disabled:opacity-70"
              >
                {signingInProvider === "demo"
                  ? "Opening demo..."
                  : "Open demo workspace"}
              </button>
              <p className="text-[11px] font-medium leading-5 text-[#73777a]">
                Google identifies your workspace. Your memories stay separated
                from every other user.
              </p>
            </div>

            <div className="mt-10 grid gap-2 sm:grid-cols-3">
              {capabilityCards.map((card) => (
                <CapabilityCard key={card.title} {...card} />
              ))}
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-4 rounded-[28px] bg-white/50 blur-2xl" />
            <div className="relative overflow-hidden rounded-[22px] border border-[#d8dbdc] bg-white shadow-[0_32px_100px_rgba(17,17,17,0.13)]">
              <div className="flex items-center justify-between border-b border-[#e5e7e8] px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-9 items-center justify-center rounded-[10px] border border-[#e2e3e4] bg-white shadow-sm">
                    <BrandIcon className="size-7" />
                  </div>
                  <div>
                    <p className="text-[13px] font-[820]">New thought</p>
                    <p className="text-[11px] font-semibold text-[#787c80]">
                      Crowscap is listening
                    </p>
                  </div>
                </div>
                <span className="size-2 rounded-full bg-[#0f5132]" />
              </div>

              <div className="space-y-4 px-4 py-5">
                <div className="ml-auto max-w-[80%] rounded-[20px_20px_6px_20px] bg-[#eef0f1] px-4 py-3 text-[13px] font-semibold leading-6 text-[#1a1c1d]">
                  This video will help with my YC application.
                </div>

                <div className="max-w-[88%] rounded-[20px_20px_20px_6px] border border-[#e2e4e5] bg-white p-4">
                  <div className="flex items-center gap-2">
                    <Check
                      size={15}
                      className="rounded-full bg-[#edf5f1] p-0.5 text-[#245e4b]"
                    />
                    <p className="text-[11px] font-extrabold uppercase text-[#303437]">
                      Memory saved
                    </p>
                  </div>
                  <p className="mt-3 text-[13px] font-medium leading-6 text-[#3f4448]">
                    I kept the link with your reason attached and will bring it
                    back when it is useful.
                  </p>
                </div>

                <div className="rounded-[16px] border border-[#e3e5e6] bg-[#fbfbfa] p-4">
                  <p className="text-[10px] font-extrabold uppercase text-[#7c8083]">
                    Ask your memory
                  </p>
                  <p className="mt-2 text-[18px] font-[760] leading-snug tracking-[-0.02em]">
                    What did I save for my YC application?
                  </p>
                  <div className="mt-4 space-y-2">
                    {proofRows.map((row) => (
                      <div key={row} className="flex items-start gap-3">
                        <span className="mt-1 size-1.5 rounded-full bg-[#111111]" />
                        <p className="text-[12px] font-semibold leading-5 text-[#42474a]">
                          {row}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-2 border-t border-[#e5e7e8] pt-4 sm:grid-cols-2">
                  <PreviewPill
                    label="Search"
                    text="Find ideas by meaning."
                    icon={<Search size={14} />}
                  />
                  <PreviewPill
                    label="Recall"
                    text="Return to one useful thought."
                    icon={<Bell size={14} />}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
        <InstallBanner />
      </section>
    </main>
  );
}

function GoogleMark() {
  return (
    <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-[#e4e6e7] bg-white">
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="size-3.5"
      >
        <path
          fill="#4285F4"
          d="M21.6 12.23c0-.78-.07-1.53-.2-2.23H12v4.22h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.9-1.75 2.98-4.32 2.98-7.52Z"
        />
        <path
          fill="#34A853"
          d="M12 22c2.7 0 4.96-.9 6.62-2.25l-3.24-2.51c-.9.6-2.05.96-3.38.96-2.6 0-4.8-1.76-5.58-4.12H3.08v2.59A9.99 9.99 0 0 0 12 22Z"
        />
        <path
          fill="#FBBC05"
          d="M6.42 14.08A6.01 6.01 0 0 1 6.1 12c0-.72.12-1.42.32-2.08V7.33H3.08A9.99 9.99 0 0 0 2 12c0 1.61.39 3.13 1.08 4.67l3.34-2.59Z"
        />
        <path
          fill="#EA4335"
          d="M12 5.8c1.47 0 2.8.5 3.84 1.5l2.87-2.87C16.96 2.8 14.7 2 12 2a9.99 9.99 0 0 0-8.92 5.33l3.34 2.59C7.2 7.56 9.4 5.8 12 5.8Z"
        />
      </svg>
    </span>
  );
}

function CapabilityCard({
  icon,
  title,
  body,
}: {
  icon: ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-[12px] border border-[#e1e3e4] bg-white/78 p-4 shadow-sm">
      <div className="flex items-center gap-2 text-[#111111]">
        {icon}
        <p className="text-[11px] font-extrabold uppercase">{title}</p>
      </div>
      <p className="mt-2 text-[12px] font-medium leading-5 text-[#64686b]">
        {body}
      </p>
    </div>
  );
}

function PreviewPill({
  icon,
  label,
  text,
}: {
  icon: ReactNode;
  label: string;
  text: string;
}) {
  return (
    <div className="rounded-[12px] border border-[#e2e4e5] bg-white p-3">
      <div className="flex items-center gap-2 text-[#111111]">
        {icon}
        <p className="text-[11px] font-extrabold uppercase">{label}</p>
      </div>
      <p className="mt-2 text-[12px] font-medium leading-5 text-[#676b6e]">
        {text}
      </p>
    </div>
  );
}
