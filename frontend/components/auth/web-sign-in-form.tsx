"use client";

import { ArrowLeft, Check } from "lucide-react";
import { signIn } from "next-auth/react";
import { useState } from "react";

import { BrandIcon } from "@/components/ui/brand-icon";

type Step = "entry" | "loading";

export function WebSignInForm() {
  const [step, setStep] = useState<Step>("entry");
  const [provider, setProvider] = useState<"google" | null>(null);

  function handleGoogleSignIn() {
    setProvider("google");
    setStep("loading");
    void signIn("google", { callbackUrl: "/" });
  }

  return (
    <main className="min-h-screen bg-[#f5f5f3] text-[#101112]">
      {/* Header */}
      <header className="mx-auto flex w-full max-w-[1220px] items-center justify-between px-5 py-5 md:px-8">
        <a href="/" className="flex items-center gap-3 transition hover:opacity-80">
          <div className="flex size-11 items-center justify-center rounded-[12px] border border-[#dedfdf] bg-white">
            <BrandIcon className="size-8" />
          </div>
          <div>
            <p className="text-[17px] font-[850] tracking-[-0.02em]">Crowscap</p>
            <p className="text-[12px] font-semibold text-[#6f7376]">
              Personal intelligent Memory
            </p>
          </div>
        </a>
        <a
          href="/"
          className="flex items-center gap-1.5 rounded-full border border-[#d9dcde] bg-white px-4 py-2 text-[12px] font-extrabold text-[#3f4447] transition hover:border-[#aeb3b5] hover:text-[#111111]"
        >
          <ArrowLeft size={13} />
          Back
        </a>
      </header>

      {/* Auth Card */}
      <div className="mx-auto flex min-h-[calc(100vh-88px)] max-w-[460px] items-center px-5 py-10">
        <div className="w-full rounded-[22px] border border-[#d8dbdc] bg-white p-8 shadow-[0_32px_100px_rgba(17,17,17,0.10)]">
          {step === "entry" ? (
            <>
              <div>
                <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-[#7d8184]">
                  Welcome back
                </p>
                <h1 className="mt-2 text-[26px] font-[860] leading-tight tracking-[-0.03em]">
                  Sign in to Crowscap
                </h1>
                <p className="mt-2 text-[13px] font-medium leading-6 text-[#555a5d]">
                  Your memory is waiting. Sign in to pick up where you left off.
                </p>
              </div>

              <div className="mt-8 flex flex-col gap-3">
                <button
                  id="web-google-signin"
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={step !== "entry"}
                  className="relative inline-flex h-12 w-full items-center justify-center rounded-[10px] border border-[#d5d8da] bg-white px-4 text-[13px] font-extrabold text-[#111111] shadow-[0_4px_20px_rgba(17,17,17,0.07)] transition hover:border-[#a8adb0] hover:bg-[#fbfbfb] disabled:cursor-wait disabled:opacity-60"
                >
                  <span className="absolute left-4">
                    <GoogleMark />
                  </span>
                  Continue with Google
                </button>
              </div>

              <div className="mt-8 space-y-3 rounded-[12px] bg-[#f8f9f9] px-4 py-4">
                {[
                  "Your memory stays private — only you can access it.",
                  "Everything you've saved is synced across devices.",
                  "No subscription needed to get started.",
                ].map((text) => (
                  <div key={text} className="flex items-start gap-2.5">
                    <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-[#edf5f1]">
                      <Check size={9} className="text-[#245e4b]" />
                    </span>
                    <p className="text-[12px] font-medium leading-5 text-[#555a5d]">{text}</p>
                  </div>
                ))}
              </div>

              <p className="mt-6 text-center text-[11px] font-medium text-[#9a9fa3]">
                By continuing, you agree to our Terms of Service and Privacy Policy.
              </p>
            </>
          ) : (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="flex size-14 items-center justify-center rounded-full bg-[#edf5f1]">
                <GoogleMark />
              </div>
              <p className="mt-5 text-[17px] font-[820] tracking-[-0.02em]">
                Opening Google…
              </p>
              <p className="mt-2 text-[13px] font-medium text-[#6f7376]">
                You will be redirected back to Crowscap after signing in.
              </p>
              <div className="mt-6 flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="size-1.5 rounded-full bg-[#111111] opacity-40"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function GoogleMark() {
  return (
    <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-[#e4e6e7] bg-white">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-3.5">
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
