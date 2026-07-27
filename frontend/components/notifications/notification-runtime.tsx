"use client";

import { Bell, BellRing, BookOpenCheck, Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import {
  connectNotificationStream,
  getPushStatus,
  registerCrowscapServiceWorker,
  showForegroundNotification,
  subscribeToPush,
  type PushStatus,
} from "@/lib/notifications";
import type { NotificationEvent } from "@/lib/types";

const statusLabel: Record<PushStatus, string> = {
  unsupported: "This browser does not support push",
  unconfigured: "Push setup pending",
  blocked: "Notifications blocked",
  ready: "Enable push",
  subscribed: "Push enabled",
};

export function NotificationRuntime() {
  const [event, setEvent] = useState<NotificationEvent | null>(null);

  useEffect(() => {
    registerCrowscapServiceWorker().catch(() => null);
    const close = connectNotificationStream(
      (nextEvent) => {
        setEvent(nextEvent);
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

  if (!event) return null;

  const Icon = event.event_type === "reminder_due" ? BellRing : BookOpenCheck;

  return (
    <div className="fixed bottom-5 left-1/2 z-50 w-[min(92vw,430px)] -translate-x-1/2 md:bottom-6 md:left-auto md:right-6 md:translate-x-0">
      <div className="rounded-lg border border-[#dfe2e4] bg-white px-4 py-3 shadow-[0_18px_60px_rgba(0,0,0,0.16)]">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-[#111111] text-white">
            <Icon size={16} strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-extrabold text-[#111111]">
              {event.title}
            </p>
            <p className="mt-1 line-clamp-2 text-[12px] leading-relaxed text-[#5d6265]">
              {event.body}
            </p>
            <div className="mt-2 flex items-center gap-3">
              <Link
                href={event.url}
                className="text-[11px] font-extrabold uppercase text-[#111111] underline-offset-4 hover:underline"
                onClick={() => setEvent(null)}
              >
                Open
              </Link>
              <button
                type="button"
                className="text-[11px] font-bold uppercase text-[#8a8d90]"
                onClick={() => setEvent(null)}
              >
                Dismiss
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
