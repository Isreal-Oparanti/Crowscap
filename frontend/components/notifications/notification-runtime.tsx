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

export function NotificationRuntime() {
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

  return null;
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
