"use client";

import { ArrowLeft, Check, Loader2, X } from "lucide-react";
import { signIn } from "next-auth/react";
import { useEffect, useState } from "react";

import { BrandIcon } from "@/components/ui/brand-icon";

type AuthMode = "signup" | "login";
type BusyState = "google" | "email-start" | "email-verify" | "resend" | null;

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "https://api.crowscap.xyz";

export function WebSignInForm() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [busy, setBusy] = useState<BusyState>(null);
  const [resendIn, setResendIn] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!resendIn) return;
    const timer = setInterval(() => {
      setResendIn((value) => Math.max(0, value - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendIn]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4200);
    return () => clearTimeout(timer);
  }, [toast]);

  async function handleGoogleSignIn() {
    setErrorMessage(null);
    setBusy("google");
    try {
      await signIn("google", { callbackUrl: "/" });
    } catch {
      setErrorMessage("Could not open Google sign in. Please try again.");
      setBusy(null);
    }
  }

  async function finishSignIn(session: { user_id: string; email: string }) {
    const res = await signIn("credentials", {
      email: session.email,
      userId: session.user_id,
      redirect: false,
      callbackUrl: "/",
    });
    if (res?.url) {
      window.location.href = res.url;
    } else {
      window.location.href = "/";
    }
  }

  async function requestEmailCode(kind: BusyState = "email-start") {
    setErrorMessage(null);
    const normalized = email.trim().toLowerCase();
    if (!normalized || !normalized.includes("@")) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    setBusy(kind);
    try {
      const resp = await fetch(`${BACKEND_URL}/api/v1/auth/email/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalized, mode }),
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Could not process request.");
      }

      if (data.status === "logged_in" && data.session) {
        await finishSignIn(data.session);
        return;
      }

      setEmail(data.email || normalized);
      setCode("");
      setCodeSent(true);
      setResendIn(data.resend_after_seconds || 60);
      setToast(`We sent a code to ${data.email || normalized}.`);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    } finally {
      setBusy(null);
    }
  }

  async function verifyEmailCode() {
    setErrorMessage(null);
    const cleanCode = code.replace(/\D/g, "");
    if (cleanCode.length !== 6) {
      setErrorMessage("Invalid verification code. Please enter 6 digits.");
      return;
    }

    setBusy("email-verify");
    try {
      const resp = await fetch(`${BACKEND_URL}/api/v1/auth/email/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          code: cleanCode,
          mode,
        }),
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Verification failed.");
      }

      await finishSignIn(data);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Verification failed. Please try again."
      );
    } finally {
      setBusy(null);
    }
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setCode("");
    setCodeSent(false);
    setToast(null);
    setErrorMessage(null);
  }

  const isSignup = mode === "signup";
  const headline = isSignup ? "Register" : "Log in";
  const busyNow = busy !== null;

  return (
    <main className="relative min-h-screen bg-[#f5f5f3] text-[#101112]">
      {/* Toast popup */}
      {toast ? (
        <div className="fixed top-5 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border border-[#d5d8da] bg-white px-5 py-2.5 text-[13px] font-bold text-[#111111] shadow-[0_12px_40px_rgba(17,17,17,0.12)]">
          <span className="flex size-4 items-center justify-center rounded-full bg-[#0f5132] text-white">
            <Check size={10} />
          </span>
          {toast}
        </div>
      ) : null}

      {/* Top Header */}
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
      <div className="mx-auto flex min-h-[calc(100vh-88px)] max-w-[440px] items-center px-5 py-8">
        <div className="w-full rounded-[22px] border border-[#d8dbdc] bg-white p-7 shadow-[0_32px_100px_rgba(17,17,17,0.10)] sm:p-9">
          {/* Logo & Headline */}
          <div className="flex flex-col items-center text-center">
            <div className="flex size-12 items-center justify-center rounded-[14px] border border-[#dedfdf] bg-white shadow-sm">
              <BrandIcon className="size-9" />
            </div>
            <h1 className="mt-4 text-[28px] font-[880] tracking-[-0.035em]">
              {headline}
            </h1>
            <p className="mt-1 text-[13px] font-semibold text-[#6f7376]">
              Your Personal Intelligent Memory
            </p>
          </div>

          {/* Google Sign In */}
          <div className="mt-7">
            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={busyNow}
              className="relative inline-flex h-12 w-full items-center justify-center rounded-[10px] border border-[#d5d8da] bg-white px-4 text-[13px] font-extrabold text-[#111111] shadow-[0_4px_20px_rgba(17,17,17,0.06)] transition hover:border-[#a8adb0] hover:bg-[#fbfbfb] disabled:cursor-wait disabled:opacity-60"
            >
              <span className="absolute left-4">
                <GoogleMark />
              </span>
              {busy === "google" ? "Opening Google..." : "Continue with Google"}
              {busy === "google" ? (
                <Loader2 size={16} className="ml-2 animate-spin text-[#111111]" />
              ) : null}
            </button>
          </div>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-[#e4e6e7]" />
            <span className="text-[11px] font-bold text-[#8a8e94]">OR</span>
            <div className="h-px flex-1 bg-[#e4e6e7]" />
          </div>

          {/* Email Input */}
          <div className="space-y-4">
            <div>
              <label className="block text-[12px] font-extrabold uppercase text-[#303437]">
                Email
              </label>
              <div className="relative mt-1.5">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setErrorMessage(null);
                    if (codeSent) {
                      setCode("");
                      setCodeSent(false);
                    }
                  }}
                  placeholder="Enter your email address"
                  disabled={busyNow}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !codeSent) {
                      void requestEmailCode();
                    }
                  }}
                  className={`h-12 w-full rounded-[10px] border bg-[#fbfbfb] px-3.5 text-[14px] font-medium text-[#111111] placeholder-[#8a8e94] outline-none transition focus:border-[#111111] focus:bg-white disabled:opacity-60 ${
                    errorMessage && !codeSent
                      ? "border-red-500"
                      : "border-[#d8dbdc]"
                  }`}
                />
                {email ? (
                  <button
                    type="button"
                    onClick={() => {
                      setEmail("");
                      setCode("");
                      setCodeSent(false);
                      setErrorMessage(null);
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8a8e94] hover:text-[#111111]"
                  >
                    <X size={16} />
                  </button>
                ) : null}
              </div>
              {errorMessage && !codeSent ? (
                <p className="mt-1.5 text-[12px] font-semibold text-red-600">
                  {errorMessage}
                </p>
              ) : null}
            </div>

            {/* Verification Code Input */}
            {codeSent ? (
              <div>
                <label className="block text-[12px] font-extrabold uppercase text-[#303437]">
                  Verification code
                </label>
                <div className="relative mt-1.5">
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    value={code}
                    onChange={(e) => {
                      setCode(e.target.value.replace(/\D/g, "").slice(0, 6));
                      setErrorMessage(null);
                    }}
                    placeholder="676767"
                    disabled={busyNow}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        void verifyEmailCode();
                      }
                    }}
                    className={`h-12 w-full rounded-[10px] border bg-[#fbfbfb] px-3.5 text-[15px] font-bold tracking-widest text-[#111111] placeholder-[#8a8e94] outline-none transition focus:border-[#111111] focus:bg-white disabled:opacity-60 ${
                      errorMessage ? "border-red-500" : "border-[#d8dbdc]"
                    }`}
                  />
                </div>
                {errorMessage ? (
                  <p className="mt-1.5 text-[12px] font-semibold text-red-600">
                    {errorMessage}
                  </p>
                ) : (
                  <p className="mt-1.5 text-[12px] font-medium text-[#6f7376]">
                    We sent a 6-digit code to your inbox
                  </p>
                )}
              </div>
            ) : null}
          </div>

          {/* Action Button */}
          <div className="mt-6">
            <button
              type="button"
              onClick={() => (codeSent ? verifyEmailCode() : requestEmailCode())}
              disabled={busyNow}
              className="flex h-12 w-full items-center justify-center rounded-[10px] bg-[#111111] px-4 text-[13px] font-extrabold text-white shadow-[0_12px_32px_rgba(17,17,17,0.15)] transition hover:bg-[#25282a] disabled:cursor-wait disabled:opacity-60"
            >
              {busy === "email-start" || busy === "email-verify" ? (
                <Loader2 size={18} className="animate-spin text-white" />
              ) : (
                "Continue"
              )}
            </button>
          </div>

          {/* Resend Code Button */}
          {codeSent ? (
            <div className="mt-3 text-center">
              <button
                type="button"
                disabled={resendIn > 0 || busyNow}
                onClick={() => requestEmailCode("resend")}
                className="text-[12px] font-bold text-[#111111] underline transition hover:text-[#555a5d] disabled:text-[#8a8e94] disabled:no-underline"
              >
                {resendIn > 0
                  ? `Resend in ${resendIn}s`
                  : "Resend verification code"}
              </button>
            </div>
          ) : null}

          {/* Mode Switcher */}
          <div className="mt-6 flex items-center justify-center gap-1.5 text-[13px]">
            <span className="font-semibold text-[#6f7376]">
              {isSignup ? "Already have an account?" : "Don't have an account?"}
            </span>
            <button
              type="button"
              onClick={() => switchMode(isSignup ? "login" : "signup")}
              className="font-extrabold text-[#111111] hover:underline"
            >
              {isSignup ? "Log in" : "Sign up"}
            </button>
          </div>

          {/* Terms Footer */}
          <p className="mt-7 text-center text-[11px] font-medium leading-4 text-[#9a9fa3]">
            By continuing, you acknowledge that you understand and agree to the
            Terms & Conditions and Privacy Policy
          </p>
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
