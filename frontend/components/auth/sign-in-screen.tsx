"use client";

import {
  ArrowRight,
  Bell,
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

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "How it works", href: "#how-it-works" },
];

const featureCards = [
  {
    icon: <FileText size={15} />,
    title: "Capture without breaking flow",
    body: "Save the link, note, PDF, video, question, or decision while the thought is still fresh.",
  },
  {
    icon: <Search size={15} />,
    title: "Ask what you already know",
    body: "Search by meaning, compare sources, and recover the exact idea without digging through folders.",
  },
  {
    icon: <Bell size={15} />,
    title: "Come back at the right time",
    body: "Recall does not flood you with a queue. It brings forward one useful thought when it can help.",
  },
];

const howItWorks = [
  {
    title: "Drop it in",
    body: "Paste a source, upload a PDF, or write the thought in plain language. Crowscap keeps the intent around it.",
  },
  {
    title: "It becomes memory",
    body: "Useful ideas are separated from noise, attached to their source, and stored as small pieces that are easy to retrieve.",
  },
  {
    title: "Use it later",
    body: "Ask a question, revisit a saved belief, or let recall bring back the next useful thing when timing matters.",
  },
];

export function SignInScreen() {
  const [signingInProvider, setSigningInProvider] = useState<
    "google" | "demo" | null
  >(null);
  const [menuOpen, setMenuOpen] = useState(false);

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

        <header className="relative z-20 mx-auto flex w-full max-w-[1220px] items-center justify-between px-5 py-5 md:px-8">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-[12px] border border-[#dedfdf] bg-white">
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
          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-2 rounded-full border border-[#dedfdf] bg-white px-3 py-1.5 text-[11px] font-extrabold text-[#4d5154] sm:flex">
              <LockKeyhole size={13} />
              Private by default
            </div>
            <button
              type="button"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((value) => !value)}
              className="group flex size-11 items-center justify-center rounded-full border border-[#d9dcde] bg-white transition hover:border-[#aeb3b5] hover:bg-[#fbfbfb]"
            >
              <span className="relative flex size-5 flex-col items-center justify-center">
                <span
                  className={`absolute h-[2px] w-5 rounded-full bg-[#111111] transition duration-200 ${
                    menuOpen ? "translate-y-0 rotate-45" : "-translate-y-2"
                  }`}
                />
                <span
                  className={`absolute h-[2px] w-4 rounded-full bg-[#111111] transition duration-200 ${
                    menuOpen ? "opacity-0" : "opacity-100"
                  }`}
                />
                <span
                  className={`absolute h-[2px] w-5 rounded-full bg-[#111111] transition duration-200 ${
                    menuOpen ? "translate-y-0 -rotate-45" : "translate-y-2"
                  }`}
                />
              </span>
            </button>
          </div>
        </header>

        {menuOpen ? (
          <div className="absolute right-5 top-[74px] z-30 w-[min(calc(100vw-40px),260px)] rounded-[16px] border border-[#d9dcde] bg-white p-2 shadow-[0_24px_70px_rgba(17,17,17,0.14)] md:right-8">
            <nav aria-label="Landing page navigation" className="grid gap-1">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="rounded-[12px] px-3 py-3 text-[13px] font-extrabold text-[#202223] transition hover:bg-[#f3f4f4]"
                >
                  {link.label}
                </a>
              ))}
            </nav>
          </div>
        ) : null}

        <div className="mx-auto grid w-full max-w-[1220px] flex-1 items-center gap-10 px-5 pb-28 pt-8 md:px-8 lg:grid-cols-[minmax(0,0.92fr)_minmax(430px,0.8fr)] lg:gap-16 lg:pb-24 lg:pt-2">
          <div className="max-w-[760px]">
            <h1 className="text-[48px] font-[880] leading-[0.95] tracking-[-0.058em] md:text-[76px] lg:text-[92px]">
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
                className="relative inline-flex h-12 items-center justify-center rounded-[10px] border border-[#d5d8da] bg-white px-4 text-center text-[13px] font-extrabold text-[#111111] shadow-[0_16px_44px_rgba(17,17,17,0.10)] transition hover:border-[#a8adb0] hover:bg-[#fbfbfb] disabled:cursor-wait disabled:opacity-70"
              >
                <span className="absolute left-4">
                  <GoogleMark />
                </span>
                {signingInProvider === "google"
                  ? "Opening Google..."
                  : "Continue with Google"}
              </button>
              <button
                type="button"
                onClick={handleDemoSignIn}
                disabled={signingInProvider !== null}
                className="inline-flex h-12 items-center justify-center rounded-[10px] border border-[#d5d8da] bg-white px-4 text-[13px] font-extrabold text-[#111111] transition hover:border-[#a8adb0] hover:bg-[#fbfbfb] disabled:cursor-wait disabled:opacity-70"
              >
                {signingInProvider === "demo"
                  ? "Opening demo..."
                  : "Open demo workspace"}
              </button>
            </div>

            <a
              href="#features"
              className="mt-7 inline-flex items-center gap-2 text-[12px] font-extrabold text-[#3f4447] transition hover:text-[#111111]"
            >
              See what it remembers
              <ArrowRight size={14} />
            </a>
          </div>

          <div className="relative">
            <div className="relative overflow-hidden rounded-[22px] border border-[#d8dbdc] bg-white shadow-[0_32px_100px_rgba(17,17,17,0.13)]">
              <div className="flex items-center justify-between border-b border-[#e5e7e8] px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-9 items-center justify-center rounded-[10px] border border-[#e2e3e4] bg-white">
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
                  This video will help my yc application
                  https://youtu.be/B5tU2447OK8
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
        <section
          id="features"
          className="border-t border-[#e1e3e4] bg-white px-5 py-16 md:px-8 md:py-22"
        >
          <div className="mx-auto grid w-full max-w-[1220px] gap-10 lg:grid-cols-[0.78fr_1.22fr] lg:gap-16">
            <div>
              <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[#7d8184]">
                Features
              </p>
              <h2 className="mt-4 max-w-[520px] text-[34px] font-[840] leading-[1.02] tracking-[-0.045em] md:text-[52px]">
                A memory layer for the things you cannot afford to lose.
              </h2>
              <p className="mt-5 max-w-[500px] text-[15px] font-medium leading-7 text-[#555a5d]">
                Crowscap is built for scattered learning: the video you meant
                to revisit, the note that changed your mind, the source you
                need before a decision, and the reminder that should not become
                clutter.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              {featureCards.map((card) => (
                <FeatureCard key={card.title} {...card} />
              ))}
            </div>
          </div>
        </section>

        <section
          id="how-it-works"
          className="border-t border-[#e1e3e4] bg-[#f5f5f3] px-5 py-16 md:px-8 md:py-22"
        >
          <div className="mx-auto w-full max-w-[1220px]">
            <div className="max-w-[680px]">
              <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[#7d8184]">
                How it works
              </p>
              <h2 className="mt-4 text-[34px] font-[840] leading-[1.02] tracking-[-0.045em] md:text-[52px]">
                Save naturally. Retrieve precisely.
              </h2>
            </div>

            <div className="mt-10 grid border-y border-[#dfe1e2] bg-white md:grid-cols-3">
              {howItWorks.map((step, index) => (
                <div
                  key={step.title}
                  className="border-b border-[#e5e7e8] p-6 md:border-b-0 md:border-r md:last:border-r-0"
                >
                  <p className="text-[11px] font-extrabold uppercase text-[#8a8e91]">
                    0{index + 1}
                  </p>
                  <h3 className="mt-5 text-[21px] font-[800] tracking-[-0.025em]">
                    {step.title}
                  </h3>
                  <p className="mt-3 text-[13px] font-medium leading-6 text-[#555a5d]">
                    {step.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <footer className="border-t border-[#dfe1e2] bg-[#101112] px-5 py-8 text-white md:px-8">
          <div className="mx-auto flex w-full max-w-[1220px] flex-col gap-8 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-[11px] border border-white/15 bg-white">
                  <BrandIcon className="size-7" />
                </div>
                <div>
                  <p className="text-[15px] font-[850]">Crowscap</p>
                  <p className="text-[11px] font-semibold text-white/55">
                    Private memory for serious learning.
                  </p>
                </div>
              </div>
              <p className="mt-5 max-w-[460px] text-[13px] font-medium leading-6 text-white/62">
                Your memory should not depend on the tab you forgot to reopen.
                Keep the idea, its source, and the reason it mattered.
              </p>
            </div>
            <div className="flex flex-col gap-4 text-[11px] font-bold text-white/62 md:items-end">
              <nav className="flex items-center gap-4" aria-label="Footer navigation">
                {navLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    className="transition hover:text-white"
                  >
                    {link.label}
                  </a>
                ))}
              </nav>
              <p>Copyright 2026 Crowscap. All rights reserved.</p>
            </div>
          </div>
        </footer>
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

function FeatureCard({
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
