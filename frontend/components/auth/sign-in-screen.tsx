"use client";

import {
  Check,
  Database,
  FileText,
  KeyRound,
  LockKeyhole,
  MessageSquareText,
  Search,
  ShieldCheck,
} from "lucide-react";
import { signIn } from "next-auth/react";
import type { ReactNode } from "react";
import { useState } from "react";

const proofPoints = [
  "Save links, PDFs, videos, notes, and conversation fragments.",
  "Turn sources into precise memory cards with evidence attached.",
  "Recall what matters when it can shape a decision.",
];

const memoryRows = [
  {
    label: "Claim",
    text: "YC interviews reward clear, conversational founder communication.",
  },
  {
    label: "Warning",
    text: "A polished answer can still fail if the founder cannot explain the customer.",
  },
  {
    label: "Action",
    text: "Review this before the application and practice the answer out loud.",
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
    <main className="min-h-screen bg-[#f5f6f7] text-[#111111]">
      <section className="relative isolate flex min-h-screen flex-col overflow-hidden border-[#111111] bg-[#f7f7f5]">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-[#d9d9d4] bg-[#f7f7f5]/90 px-5 backdrop-blur md:h-[76px] md:px-10">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-[10px] bg-[#111111] text-white shadow-[0_10px_24px_rgba(17,17,17,0.14)]">
              <Database size={18} strokeWidth={2} />
            </div>
            <div>
              <p className="text-[15px] font-[820] tracking-[-0.01em]">
                Crowscap
              </p>
              <p className="text-[11px] font-semibold text-[#737373]">
                Personal memory intelligence
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-[#d4d4cf] bg-white px-3 py-1.5 text-[10px] font-extrabold uppercase text-[#555555] md:flex">
            <LockKeyhole size={13} />
            Private workspace
          </div>
        </header>

        <div className="grid flex-1 lg:grid-cols-[minmax(0,0.92fr)_minmax(520px,1.08fr)]">
          <div className="flex flex-col justify-between px-6 py-10 md:px-10 md:py-12 lg:py-14">
            <div>
              <p className="inline-flex items-center gap-2 border-b border-[#111111] pb-2 text-[11px] font-extrabold uppercase tracking-[0.12em] text-[#111111]">
                <ShieldCheck size={14} />
                Memory you can defend
              </p>
              <h1 className="mt-8 max-w-[780px] text-[48px] font-[860] leading-[0.96] tracking-[-0.055em] md:text-[76px] lg:text-[86px]">
                Your saved learning, made usable.
              </h1>
              <p className="mt-7 max-w-[620px] text-[16px] font-medium leading-8 text-[#4d4d4d] md:text-[18px]">
                Crowscap remembers the sources, ideas, doubts, and decisions you
                do not want to lose, then brings them back when they can change
                how you think or act.
              </p>

              <div className="mt-8 grid max-w-[640px] gap-3">
                {proofPoints.map((point) => (
                  <div
                    key={point}
                    className="flex items-start gap-3 text-[13px] font-semibold leading-6 text-[#333333]"
                  >
                    <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-[#111111] text-white">
                      <Check size={12} strokeWidth={2.4} />
                    </span>
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-10 flex flex-col gap-3 sm:max-w-[420px]">
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={signingInProvider !== null}
                className="inline-flex h-12 items-center justify-center gap-3 rounded-md bg-[#111111] px-4 text-[13px] font-extrabold text-white shadow-[0_18px_44px_rgba(17,17,17,0.18)] transition hover:bg-black disabled:cursor-wait disabled:opacity-70"
              >
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-white text-[12px] font-black text-[#111111]">
                  G
                </span>
                <span className="text-white">
                  {signingInProvider === "google"
                    ? "Opening Google..."
                    : "Continue with Google"}
                </span>
              </button>
              <button
                type="button"
                onClick={handleDemoSignIn}
                disabled={signingInProvider !== null}
                className="inline-flex h-12 items-center justify-center gap-3 rounded-md border border-[#d9d9d4] bg-white px-4 text-[13px] font-extrabold text-[#111111] transition hover:border-[#111111] disabled:cursor-wait disabled:opacity-70"
              >
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-[#111111] text-[12px] font-black text-white">
                  D
                </span>
                <span>
                  {signingInProvider === "demo"
                    ? "Signing in..."
                    : "Open demo workspace"}
                </span>
              </button>
              <p className="text-[11px] font-medium leading-5 text-[#777777]">
                Google is used only to identify your workspace. Your saved
                memory is separated from every other user.
              </p>
            </div>
          </div>

          <div className="flex min-h-[620px] flex-col border-t border-[#d9d9d4] bg-[#111111] p-4 text-white md:p-6 lg:border-l lg:border-t-0 lg:p-8">
            <ProductSurface />
          </div>
        </div>
      </section>
    </main>
  );
}

function ProductSurface() {
  return (
    <div className="flex min-h-full flex-col rounded-[10px] border border-[#2b2b2b] bg-[#151515] shadow-[0_30px_90px_rgba(0,0,0,0.35)]">
      <div className="flex h-12 items-center justify-between border-b border-[#2b2b2b] px-4">
        <div className="flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-[#f2f2f2]" />
          <span className="size-2.5 rounded-full bg-[#8a8a8a]" />
          <span className="size-2.5 rounded-full bg-[#4a4a4a]" />
        </div>
        <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[#a8a8a8]">
          Live memory workspace
        </p>
      </div>

      <div className="grid flex-1 gap-0 md:grid-cols-[1fr_260px]">
        <div className="flex min-h-[540px] flex-col px-4 py-5 md:px-6">
          <div className="max-w-[82%] rounded-[16px] rounded-bl-[4px] bg-[#222222] px-4 py-3 text-[13px] font-semibold leading-6 text-[#f5f5f5]">
            This video will help with my YC application.
            <span className="mt-2 block text-[#bcbcbc]">
              https://youtu.be/founder-interview
            </span>
          </div>

          <div className="mt-5 max-w-[92%] rounded-[16px] rounded-tl-[4px] border border-[#3a3a3a] bg-[#191919] p-4">
            <div className="flex items-center gap-2 text-[#e8e8e8]">
              <FileText size={15} />
              <p className="text-[11px] font-extrabold uppercase">
                Memory receipt
              </p>
            </div>
            <p className="mt-3 text-[13px] font-semibold leading-6 text-[#d8d8d8]">
              Saved with your reason attached. Crowscap will bring it back when
              you are preparing the application.
            </p>
          </div>

          <div className="mt-6 grid gap-3">
            {memoryRows.map((row) => (
              <div
                key={row.text}
                className="rounded-[8px] border border-[#343434] bg-[#1d1d1d] p-4"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-extrabold uppercase tracking-[0.08em] text-[#bdbdbd]">
                    {row.label}
                  </span>
                  <span className="h-px flex-1 bg-[#333333]" />
                </div>
                <p className="mt-3 text-[13px] font-medium leading-6 text-[#eeeeee]">
                  {row.text}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-auto grid gap-3 pt-6 sm:grid-cols-3">
            <Metric label="Sources saved" value="47" />
            <Metric label="Due recalls" value="3" />
            <Metric label="Tensions found" value="8" />
          </div>
        </div>

        <aside className="border-t border-[#2b2b2b] bg-[#101010] p-4 md:border-l md:border-t-0">
          <div className="flex items-center gap-2 text-[#f0f0f0]">
            <Search size={15} />
            <p className="text-[10px] font-extrabold uppercase tracking-[0.12em]">
              What Crowscap holds
            </p>
          </div>
          <div className="mt-5 space-y-3">
            <Signal
              icon={<MessageSquareText size={14} />}
              label="Recent context"
              text="YC application, founder clarity, saved interview advice"
            />
            <Signal
              icon={<KeyRound size={14} />}
              label="Preference"
              text="Direct answers, practical application, stronger evidence"
            />
            <Signal
              icon={<LockKeyhole size={14} />}
              label="Boundary"
              text="Each memory belongs to the signed-in workspace"
            />
          </div>

          <div className="mt-8 border-t border-[#2b2b2b] pt-5">
            <p className="text-[10px] font-extrabold uppercase tracking-[0.12em] text-[#a8a8a8]">
              Next useful nudge
            </p>
            <p className="mt-3 text-[19px] font-[760] leading-tight text-white">
              Review the YC video before drafting your application.
            </p>
            <p className="mt-3 text-[12px] font-medium leading-5 text-[#a8a8a8]">
              Scheduled for tomorrow morning.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-[#383838] pt-3">
      <p className="text-[24px] font-[820] leading-none text-white">{value}</p>
      <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.08em] text-[#9d9d9d]">
        {label}
      </p>
    </div>
  );
}

function Signal({
  icon,
  label,
  text,
}: {
  icon: ReactNode;
  label: string;
  text: string;
}) {
  return (
    <div className="rounded-[8px] border border-[#303030] bg-[#171717] p-3">
      <div className="flex items-center gap-2 text-[#d8d8d8]">
        {icon}
        <p className="text-[10px] font-extrabold uppercase tracking-[0.08em]">
          {label}
        </p>
      </div>
      <p className="mt-2 text-[12px] font-medium leading-5 text-[#b5b5b5]">
        {text}
      </p>
    </div>
  );
}
