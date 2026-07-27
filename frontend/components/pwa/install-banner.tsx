"use client";

import { Download, Smartphone, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

const DISMISS_KEY = "crowscap:pwa-install-dismissed";

export function InstallBanner() {
  const [promptEvent, setPromptEvent] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [installing, setInstalling] = useState(false);

  const iosHint = useMemo(() => {
    if (typeof window === "undefined") return false;
    const ua = window.navigator.userAgent.toLowerCase();
    const isAppleMobile = /iphone|ipad|ipod/.test(ua);
    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone);
    return isAppleMobile && !isStandalone;
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(DISMISS_KEY) === "1") return;

    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone);

    if (isStandalone) return;

    const onPrompt = (event: Event) => {
      event.preventDefault();
      setPromptEvent(event as BeforeInstallPromptEvent);
      setVisible(true);
    };

    const onInstalled = () => {
      setVisible(false);
      setPromptEvent(null);
    };

    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);

    const fallback = window.setTimeout(() => setVisible(true), 1200);

    return () => {
      window.clearTimeout(fallback);
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, [iosHint]);

  if (!visible) return null;

  const canPrompt = Boolean(promptEvent);

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 px-4 pb-4 sm:px-6">
      <div className="mx-auto flex max-w-[960px] items-center gap-3 rounded-[12px] border border-[#dfe2e4] bg-white px-4 py-3 shadow-[0_20px_70px_rgba(17,17,17,0.18)]">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-[10px] bg-[#111111] text-white">
          <Smartphone size={18} strokeWidth={2.1} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-[820] text-[#111111]">
            Install Crowscap
          </p>
          <p className="mt-0.5 text-[12px] font-medium leading-5 text-[#62666a]">
            {canPrompt
              ? "Open it like a native app and come back from reminders faster."
              : iosHint
                ? "On iPhone, tap Share, then Add to Home Screen."
                : "Use the install icon in your browser bar when it appears."}
          </p>
        </div>
        {canPrompt ? (
          <button
            type="button"
            disabled={installing}
            className="hidden h-10 items-center gap-2 rounded-md bg-[#111111] px-4 text-[12px] font-extrabold text-white transition hover:bg-black disabled:cursor-wait disabled:opacity-70 sm:inline-flex"
            onClick={async () => {
              if (!promptEvent) return;
              setInstalling(true);
              try {
                await promptEvent.prompt();
                const choice = await promptEvent.userChoice;
                if (choice.outcome === "accepted") {
                  setVisible(false);
                }
              } finally {
                setInstalling(false);
              }
            }}
          >
            <Download size={15} />
            {installing ? "Opening..." : "Install"}
          </button>
        ) : null}
        <button
          type="button"
          aria-label="Dismiss install prompt"
          className="flex size-9 shrink-0 items-center justify-center rounded-md text-[#62666a] transition hover:bg-[#f0f1f2] hover:text-[#111111]"
          onClick={() => {
            window.localStorage.setItem(DISMISS_KEY, "1");
            setVisible(false);
          }}
        >
          <X size={17} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
