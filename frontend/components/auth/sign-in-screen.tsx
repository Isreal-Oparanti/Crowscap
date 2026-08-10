"use client";

import {
  ArrowRight,
  Bell,
  Check,
  FileText,
  Search,
} from "lucide-react";
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

function AndroidIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 10h.01M14 10h.01M12 2a9 9 0 0 0-9 9v11l3-3 3 3 3-3 3 3 3-3 3 3V11a9 9 0 0 0-9-9z" />
    </svg>
  );
}

function PreviewPill({ label, text, icon }: { label: string; text: string; icon: ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-[12px] border border-[#e2e4e5] bg-white p-3">
      <div className="flex size-7 shrink-0 items-center justify-center rounded-[8px] bg-[#f5f5f5]">
        {icon}
      </div>
      <div>
        <p className="text-[11px] font-extrabold uppercase text-[#303437]">{label}</p>
        <p className="text-[11px] font-medium text-[#6f7376]">{text}</p>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-[18px] border border-[#e2e4e5] bg-[#fbfbfb] p-5">
      <div className="flex size-8 items-center justify-center rounded-[9px] border border-[#dcdfe0] bg-white">
        {icon}
      </div>
      <h3 className="mt-4 text-[15px] font-extrabold tracking-tight text-[#111111]">{title}</h3>
      <p className="mt-2 text-[13px] font-medium leading-6 text-[#555a5d]">{body}</p>
    </div>
  );
}

export function SignInScreen({ isLoggedIn = false }: { isLoggedIn?: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [downloadStarted, setDownloadStarted] = useState(false);

  const appHref = isLoggedIn ? "/chat" : "/auth?mode=login";
  const buttonLabel = "Chat";

  function handleDownload() {
    setDownloadStarted(true);
    const link = document.createElement("a");
    link.href = "/downloads/crowscap-release.apk";
    link.download = "crowscap-release.apk";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return (
    <div className="relative min-h-screen bg-[#f5f5f3] text-[#111111] antialiased">
      <InstallBanner />

      <main className="relative z-10 flex min-h-screen flex-col">
        {/* Top Announcement Bar / Minimal Web Header */}
        <header className="mx-auto flex w-full max-w-[1220px] items-center justify-between px-5 py-5 md:px-8">
          <a href="/" className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-[12px] border border-[#dedfdf] bg-white">
              <BrandIcon className="size-8 text-[#111111]" />
            </div>
            <div>
              <p className="text-[17px] font-[850] tracking-[-0.02em]">
                Crowscap AI
              </p>
              <p className="text-[12px] font-semibold text-[#6f7376]">
                Personal intelligent Memory
              </p>
            </div>
          </a>

          {/* Desktop Navigation Links */}
          <nav aria-label="Desktop navigation" className="hidden items-center gap-7 md:flex">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-[13px] font-extrabold text-[#3f4447] transition hover:text-[#111111]"
              >
                {link.label}
              </a>
            ))}
            <a
              href="mailto:support@crowscap.xyz"
              className="text-[13px] font-extrabold text-[#3f4447] transition hover:text-[#111111]"
            >
              Contact
            </a>
            <a
              href={appHref}
              className="rounded-full bg-[#111111] px-5 py-2 text-[12px] font-extrabold text-white transition hover:bg-[#282a2c]"
            >
              {buttonLabel}
            </a>
          </nav>

          {/* Mobile Hamburger Button */}
          <div className="flex items-center gap-2 md:hidden">
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
          <div className="absolute right-5 top-[74px] z-30 w-[min(calc(100vw-40px),260px)] rounded-[16px] border border-[#d9dcde] bg-white p-2 shadow-[0_24px_70px_rgba(17,17,17,0.14)] md:hidden">
            <nav aria-label="Mobile navigation" className="grid gap-1">
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
              <a
                href="mailto:support@crowscap.xyz"
                onClick={() => setMenuOpen(false)}
                className="rounded-[12px] px-3 py-3 text-[13px] font-extrabold text-[#202223] transition hover:bg-[#f3f4f4]"
              >
                Contact
              </a>
              <a
                href={appHref}
                onClick={() => setMenuOpen(false)}
                className="mt-1 rounded-[12px] bg-[#111111] px-3 py-3 text-center text-[13px] font-extrabold text-white transition hover:bg-[#25282a]"
              >
                {buttonLabel}
              </a>
            </nav>
          </div>
        ) : null}

        <div className="mx-auto grid w-full max-w-[1220px] flex-1 items-center gap-10 px-5 pb-20 pt-8 md:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(400px,0.85fr)] lg:gap-14 lg:pb-20 lg:pt-4">
          <div className="max-w-[580px] lg:border-r lg:border-[#e2e4e5] lg:pr-12">
            <h1 className="text-[36px] font-[880] leading-[1.02] tracking-[-0.045em] sm:text-[46px] md:text-[54px] lg:text-[62px]">
              Stop losing what you learn. Start actually using it.
            </h1>
            <p className="mt-6 text-[15px] font-medium leading-7 text-[#464a4d] md:text-[17px]">
              Crowscap AI is your personal intelligent memory that saves what you read and watch, 
              connects it to what you already know, 
              and brings the right idea back the moment you actually need it.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:max-w-[430px]">
              {/* TOP BUTTON: Download the App */}
              <button
                type="button"
                onClick={handleDownload}
                disabled={downloadStarted}
                className="relative inline-flex h-12 items-center justify-center gap-2 rounded-[10px] border border-[#d5d8da] bg-white px-4 text-[13px] font-extrabold text-[#111111] transition hover:border-[#a8adb0] hover:bg-[#fbfbfb] disabled:cursor-default"
              >
                {downloadStarted ? (
                  <>
                    <span className="flex size-4 items-center justify-center rounded-full bg-[#0f5132]">
                      <Check size={10} className="text-white" />
                    </span>
                    Download started...
                  </>
                ) : (
                  <>
                    <AndroidIcon />
                    Download the App
                  </>
                )}
              </button>

              {/* BOTTOM BUTTON: Continue on Web */}
              <a
                href={appHref}
                className="relative inline-flex h-12 items-center justify-center rounded-[10px] bg-[#111111] px-4 text-center text-[13px] font-extrabold text-white transition hover:bg-[#1f2122]"
              >
                Continue on Web
                <span className="absolute right-4 flex size-5 items-center justify-center">
                  <ArrowRight size={14} />
                </span>
              </a>
            </div>

            <a
              href="#features"
              className="mt-6 inline-flex items-center gap-2 text-[12px] font-extrabold text-[#3f4447] transition hover:text-[#111111]"
            >
              See what it remembers
              <ArrowRight size={14} />
            </a>
          </div>

          <div className="relative">
            <div className="relative overflow-hidden rounded-[22px] border border-[#d8dbdc] bg-white">
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
          <div className="mx-auto grid w-full max-w-[1220px] items-start gap-10 lg:grid-cols-[0.78fr_1.22fr] lg:gap-16">
            <div>
              <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[#7d8184]">
                Features
              </p>
              <h2 className="mt-4 max-w-[520px] text-[32px] font-[840] leading-[1.05] tracking-[-0.04em] md:text-[46px]">
                A memory layer for the things you cannot afford to lose.
              </h2>
              <p className="mt-5 max-w-[500px] text-[15px] font-medium leading-7 text-[#555a5d]">
                Crowscap is built for scattered learning: the video you meant
                to revisit, the note that changed your mind, the source you
                need before a decision, and the reminder that should not become
                clutter.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-3 items-start">
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
              <h2 className="mt-4 text-[32px] font-[840] leading-[1.05] tracking-[-0.04em] md:text-[46px]">
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

        <footer className="border-t border-[#333537] bg-[#101112] px-5 py-14 text-white md:px-8">
          <div className="mx-auto grid w-full max-w-[1220px] gap-10 md:grid-cols-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-[11px] border border-white/15 bg-white">
                  <BrandIcon className="size-7 text-[#111111]" />
                </div>
                <div>
                  <p className="text-[16px] font-[850]">Crowscap AI</p>
                  <p className="text-[11px] font-semibold text-white/55">
                    Personal intelligent Memory
                  </p>
                </div>
              </div>
              <p className="mt-4 max-w-[360px] text-[13px] font-medium leading-6 text-white/60">
                Your memory should not depend on the tab you forgot to reopen.
                Keep the idea, its source, and the reason it mattered.
              </p>
            </div>

            <div>
              <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-white/40">
                Navigation
              </p>
              <ul className="mt-4 space-y-2.5 text-[13px] font-semibold text-white/70">
                <li>
                  <a href="#features" className="transition hover:text-white">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#how-it-works" className="transition hover:text-white">
                    How it works
                  </a>
                </li>
                <li>
                  <a href={appHref} className="transition hover:text-white">
                    Open Web App
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-white/40">
                Legal
              </p>
              <ul className="mt-4 space-y-2.5 text-[13px] font-semibold text-white/70">
                <li>
                  <a href="/terms" className="transition hover:text-white">
                    Terms &amp; Conditions
                  </a>
                </li>
                <li>
                  <a href="/privacy" className="transition hover:text-white">
                    Privacy Policy
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-white/40">
                Contact &amp; Support
              </p>
              <div className="mt-4 space-y-2.5 text-[13px] font-semibold">
                <p className="text-white/60">Have questions or feedback?</p>
                <a
                  href="mailto:support@crowscap.xyz"
                  className="inline-block rounded-lg border border-white/20 bg-white/5 px-3.5 py-2 text-[13px] font-extrabold text-white transition hover:border-white/40 hover:bg-white/10"
                >
                  support@crowscap.xyz
                </a>
              </div>
            </div>
          </div>

          <div className="mx-auto mt-12 flex w-full max-w-[1220px] flex-col items-center justify-between border-t border-white/10 pt-6 text-[12px] font-medium text-white/45 sm:flex-row">
            <p>© 2026 Crowscap. All rights reserved.</p>
            <div className="mt-2 flex gap-5 sm:mt-0">
              <a href="/terms" className="transition hover:text-white">Terms &amp; Conditions</a>
              <a href="/privacy" className="transition hover:text-white">Privacy Policy</a>
            </div>
          </div>
        </footer>
        <InstallBanner />
      </main>
    </div>
  );
}
