"use client";

import {
  ArrowRight,
  Check,
  FileText,
  LockKeyhole,
  MessageSquareText,
  Search,
} from "lucide-react";
import { signIn } from "next-auth/react";
import type { ReactNode } from "react";
import { useState } from "react";

import { InstallBanner } from "@/components/pwa/install-banner";
import { BrandIcon } from "@/components/ui/brand-icon";

const memoryRows = [
  "Keep the video for my YC application.",
  "Remind me before the deadline.",
  "Surface the strongest ideas when I need them.",
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
    <main className="min-h-screen bg-[#f7f7f5] text-[#111111]">
      <section className="relative flex min-h-screen flex-col overflow-hidden px-5 pb-28 pt-5 md:px-8 md:pb-24">
        <header className="mx-auto flex w-full max-w-[1180px] items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-[12px] border border-[#e2e3e4] bg-white shadow-[0_10px_26px_rgba(17,17,17,0.12)]">
              <BrandIcon className="size-8" />
            </div>
            <div>
              <p className="text-[17px] font-[850] tracking-[-0.02em]">
                Crowscap
              </p>
              <p className="text-[12px] font-semibold text-[#707477]">
                Personal intelligence
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-[#dedfdf] bg-white px-3 py-1.5 text-[11px] font-extrabold text-[#4d5154] shadow-sm sm:flex">
            <LockKeyhole size={13} />
            Private by default
          </div>
        </header>

        <div className="mx-auto grid w-full max-w-[1180px] flex-1 items-center gap-10 py-12 lg:grid-cols-[minmax(0,0.94fr)_minmax(430px,0.78fr)] lg:py-0">
          <div>
            <p className="text-[11px] font-extrabold uppercase tracking-[0.18em] text-[#0f5132]">
              Source-aware memory
            </p>
            <h1 className="mt-6 max-w-[760px] text-[48px] font-[880] leading-[0.95] tracking-[-0.058em] md:text-[74px] lg:text-[86px]">
              Keep what matters. Use it when it matters.
            </h1>
            <p className="mt-7 max-w-[660px] text-[17px] font-medium leading-8 text-[#464a4d] md:text-[19px]">
              Crowscap turns saved links, notes, videos, PDFs, decisions, and
              reminders into a private memory you can search, question, revisit,
              and act on.
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:max-w-[430px]">
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={signingInProvider !== null}
                className="group inline-flex h-12 items-center justify-between rounded-[8px] bg-[#111111] px-4 text-[13px] font-extrabold text-white shadow-[0_18px_44px_rgba(17,17,17,0.18)] transition hover:bg-black disabled:cursor-wait disabled:opacity-70"
              >
                <span className="inline-flex items-center gap-3">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-white text-[12px] font-black text-[#111111]">
                    G
                  </span>
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
                className="inline-flex h-12 items-center justify-center rounded-[8px] border border-[#d8dadb] bg-white px-4 text-[13px] font-extrabold text-[#111111] transition hover:border-[#111111] disabled:cursor-wait disabled:opacity-70"
              >
                {signingInProvider === "demo"
                  ? "Opening demo..."
                  : "Open demo workspace"}
              </button>
              <p className="text-[11px] font-medium leading-5 text-[#73777a]">
                Google only identifies your workspace. Your memories stay
                separated from every other user.
              </p>
            </div>
          </div>

          <div className="rounded-[18px] border border-[#dfe1e2] bg-white p-3 shadow-[0_26px_90px_rgba(17,17,17,0.12)]">
            <div className="rounded-[14px] border border-[#eceeef] bg-[#fbfbfa]">
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
                <div className="ml-auto max-w-[78%] rounded-[18px_18px_4px_18px] bg-[#111111] px-4 py-3 text-[13px] font-semibold leading-6 text-white">
                  This video will help with my YC application.
                </div>
                <div className="max-w-[86%] rounded-[18px_18px_18px_4px] border border-[#e3e5e6] bg-white p-4">
                  <div className="flex items-center gap-2">
                    <FileText size={15} />
                    <p className="text-[11px] font-extrabold uppercase text-[#303437]">
                      Memory receipt
                    </p>
                  </div>
                  <p className="mt-3 text-[13px] font-medium leading-6 text-[#3f4448]">
                    Saved with your reason attached. I will bring it back when
                    you are preparing the application.
                  </p>
                </div>

                <div className="grid gap-2">
                  {memoryRows.map((row) => (
                    <div
                      key={row}
                      className="flex items-start gap-3 rounded-[10px] border border-[#e3e5e6] bg-white px-3 py-3"
                    >
                      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-[#eef5f1] text-[#0f5132]">
                        <Check size={12} strokeWidth={2.3} />
                      </span>
                      <p className="text-[12px] font-semibold leading-5 text-[#33383b]">
                        {row}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-2 border-t border-[#e5e7e8] pt-4 sm:grid-cols-2">
                  <PreviewPill
                    icon={<Search size={14} />}
                    label="Search memory"
                    text="Find the idea, not just the keyword."
                  />
                  <PreviewPill
                    icon={<MessageSquareText size={14} />}
                    label="Recall"
                    text="One useful nudge at the right time."
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
    <div className="rounded-[10px] border border-[#e2e4e5] bg-white p-3">
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
