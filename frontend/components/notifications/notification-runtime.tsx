"use client";

import { Bell, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import {
  connectNotificationStream,
  getPushStatus,
  registerCrowscapServiceWorker,
  showForegroundNotification,
  subscribeToPush,
  type PushStatus,
} from "@/lib/notifications";
const statusLabel: Record<PushStatus, string> = {
  unsupported: "This browser does not support push",
  unconfigured: "Push setup pending",
  blocked: "Notifications blocked",
  ready: "Enable push",
  subscribed: "Push enabled",
};

const PWA_INSTALLED_KEY = "crowscap:pwa-installed";
const PUSH_DISMISS_KEY = "crowscap:push-prompt-dismissed-until";
const PUSH_DISMISS_DAYS = 7;

function isStandalonePwa() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone)
  );
}

function hasInstalledMemory() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(PWA_INSTALLED_KEY) === "true";
}

function isPushPromptDismissed() {
  if (typeof window === "undefined") return true;
  const until = Number(window.localStorage.getItem(PUSH_DISMISS_KEY) || 0);
  return until > Date.now();
}

function dismissPushPrompt() {
  if (typeof window === "undefined") return;
  const until = Date.now() + PUSH_DISMISS_DAYS * 24 * 60 * 60 * 1000;
  window.localStorage.setItem(PUSH_DISMISS_KEY, String(until));
}

export function NotificationRuntime() {
  const [showPushPrompt, setShowPushPrompt] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);

  useEffect(() => {
    registerCrowscapServiceWorker().catch(() => null);
    const close = connectNotificationStream(
      (nextEvent) => {
        window.dispatchEvent(
          new CustomEvent("crowscap:notification-event", {
            detail: nextEvent,
          }),
        );
        showForegroundNotification(nextEvent).catch(() => null);
      },
      () => undefined,
    );
    return close;
  }, []);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let mounted = true;

    const evaluatePrompt = async () => {
      if (typeof window === "undefined") return;
      if (!isStandalonePwa() && !hasInstalledMemory()) return;
      if (isPushPromptDismissed()) return;

      const status = await getPushStatus().catch(() => "unconfigured" as PushStatus);
      if (mounted && status === "ready") {
        timeout = setTimeout(() => setShowPushPrompt(true), 1200);
      }
    };

    const onInstalled = () => {
      void evaluatePrompt();
    };

    window.addEventListener("crowscap:pwa-installed", onInstalled);
    void evaluatePrompt();

    return () => {
      mounted = false;
      if (timeout) clearTimeout(timeout);
      window.removeEventListener("crowscap:pwa-installed", onInstalled);
    };
  }, []);

  if (!showPushPrompt) return null;

  return (
    <div className="fixed bottom-5 left-4 right-4 z-[110] mx-auto max-w-md md:bottom-6 md:left-auto md:right-6">
      <div className="rounded-2xl border border-[#dfe2e4] bg-white p-4 shadow-[0_18px_54px_rgba(17,17,17,0.16)]">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-[10px] bg-[#111111] text-white">
            <Bell size={18} strokeWidth={2.1} />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-[820] text-[#111111]">
              Let Crowscap bring memories back
            </h3>
            <p className="mt-1 text-[13px] font-medium leading-5 text-[#62666a]">
              Get notified when a reminder or important recall is ready.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                disabled={pushLoading}
                style={{ color: "#ffffff" }}
                className="rounded-full bg-[#111111] px-4 py-2 text-sm font-semibold !text-white transition hover:bg-black disabled:opacity-60"
                onClick={async () => {

                  try {
                    setPushLoading(true);
                    const status = await subscribeToPush();
                    if (status === "subscribed") {
                      setShowPushPrompt(false);
                    }
                  } finally {
                    setPushLoading(false);
                  }
                }}
              >
                {pushLoading ? "Opening..." : "Allow reminders"}
              </button>
              <button
                type="button"
                className="rounded-full px-3 py-2 text-sm font-semibold text-[#6f7376] transition hover:bg-[#f2f3f4] hover:text-[#111111]"
                onClick={() => {
                  dismissPushPrompt();
                  setShowPushPrompt(false);
                }}
              >
                Not now
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function PushNotificationControl() {
  const [status, setStatus] = useState<PushStatus>("unsupported");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    getPushStatus()
      .then((nextStatus) => {
        if (active) setStatus(nextStatus);
      })
      .catch(() => {
        if (active) setStatus("unconfigured");
      });
    return () => {
      active = false;
    };
  }, []);

  const actionable = status === "ready";

  return (
    <button
      type="button"
      disabled={!actionable || busy}
      className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left transition ${
        actionable
          ? "border-[#cfd3d7] bg-white text-[#111111] hover:border-[#111111]"
          : "border-[#e2e4e5] bg-[#f7f8f8] text-[#777a7e]"
      }`}
      onClick={async () => {
        if (!actionable) return;
        setBusy(true);
        try {
          setStatus(await subscribeToPush());
        } finally {
          setBusy(false);
        }
      }}
    >
      <span>
        <span className="block text-[10px] font-extrabold uppercase">
          Notifications
        </span>
        <span className="mt-0.5 block text-[11px] font-semibold">
          {statusLabel[status]}
        </span>
      </span>
      {busy ? (
        <Loader2 size={15} className="animate-spin" />
      ) : (
        <Bell size={15} strokeWidth={2} />
      )}
    </button>
  );
}
