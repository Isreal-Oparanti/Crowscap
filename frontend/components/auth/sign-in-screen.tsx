"use client";

import { ArrowRight, BrainCircuit, LockKeyhole, ShieldCheck } from "lucide-react";
import { signIn } from "next-auth/react";
import { useState } from "react";

export function SignInScreen() {
  const [isSigningIn, setIsSigningIn] = useState(false);

  function handleGoogleSignIn() {
    setIsSigningIn(true);
    void signIn("google", { callbackUrl: "/" }).finally(() => {
      setIsSigningIn(false);
    });
  }

  return (
    <main className="min-h-screen bg-[#f5f6f7] px-4 py-5 text-[#111111] md:px-8 md:py-8">
      <div className="mx-auto flex min-h-[calc(100vh-40px)] max-w-6xl flex-col rounded-[18px] border border-[#e2e4e5] bg-white shadow-[0_24px_80px_rgba(17,17,17,0.08)]">
        <header className="flex items-center justify-between border-b border-[#eceeef] px-5 py-4 md:px-7">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-[#111111] text-white shadow-[0_8px_22px_rgba(17,17,17,0.16)]">
              <BrainCircuit size={19} />
            </div>
            <div>
              <p className="text-[15px] font-[780]">Crowscap</p>
              <p className="text-[11px] font-semibold text-[#767a7d]">
                Personal intelligence
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-[#e1e3e4] px-3 py-1.5 text-[10px] font-extrabold uppercase text-[#62676a] md:flex">
            <LockKeyhole size={13} />
            Private by default
          </div>
        </header>

        <section className="grid flex-1 items-stretch md:grid-cols-[1.05fr_0.95fr]">
          <div className="flex flex-col justify-center px-6 py-12 md:px-12 lg:px-16">
            <p className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-[#2d7058]">
              Source-aware memory
            </p>
            <h1 className="mt-5 max-w-2xl text-[42px] font-[820] leading-[1.03] md:text-[58px]">
              Your learning, protected and ready when it matters.
            </h1>
            <p className="mt-5 max-w-xl text-[15px] font-medium leading-7 text-[#5f6467]">
              Crowscap turns saved links, notes, videos, PDFs, and conversations
              into private memory you can search, revisit, question, and use.
            </p>

            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={isSigningIn}
              className="mt-9 inline-flex h-12 w-full max-w-sm items-center justify-between gap-3 rounded-lg border border-[#111111] bg-white px-4 text-[13px] font-extrabold text-[#111111] shadow-[0_14px_38px_rgba(17,17,17,0.08)] transition hover:bg-[#f7f8f8] disabled:cursor-wait disabled:opacity-70"
            >
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-[#dfe2e3] bg-white text-[12px] font-black text-[#111111]">
                G
              </span>
              <span className="min-w-0 flex-1 text-center">
                {isSigningIn ? "Opening Google..." : "Continue with Google"}
              </span>
              <ArrowRight className="shrink-0" size={16} />
            </button>

            <p className="mt-4 max-w-sm text-[11px] font-medium leading-5 text-[#8b8f92]">
              We use Google only to identify your workspace. Your memories stay
              separated from every other user.
            </p>
          </div>

          <div className="border-t border-[#eceeef] bg-[#fafafa] p-5 md:border-l md:border-t-0 md:p-8">
            <div className="flex h-full flex-col justify-end rounded-2xl border border-[#e1e3e4] bg-white p-5 shadow-[0_18px_60px_rgba(17,17,17,0.06)]">
              <div className="rounded-xl border border-[#d9e5df] bg-[#f0f7f3] p-4">
                <div className="flex items-center gap-2 text-[#2d7058]">
                  <ShieldCheck size={16} />
                  <p className="text-[10px] font-extrabold uppercase">
                    Memory boundary
                  </p>
                </div>
                <p className="mt-3 text-[13px] font-semibold leading-6 text-[#3f5d51]">
                  Every chat, capture, recall, preference, and search is tied to
                  the signed-in user before it reaches the backend.
                </p>
              </div>
              <div className="mt-4 grid gap-3 text-[12px] font-semibold text-[#4f5558]">
                <p className="rounded-xl border border-[#eceeef] p-4">
                  Capture what you read without turning everything into noise.
                </p>
                <p className="rounded-xl border border-[#eceeef] p-4">
                  Ask what you know, where your sources disagree, and what needs
                  stronger evidence.
                </p>
                <p className="rounded-xl border border-[#eceeef] p-4">
                  Come back to one useful thought at a time, not another queue.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
