"use client";

import {
  getPushPublicKey,
  removePushSubscription,
  savePushSubscription,
} from "@/lib/api";
import type { NotificationEvent } from "@/lib/types";

export type PushStatus =
  | "unsupported"
  | "unconfigured"
  | "blocked"
  | "ready"
  | "subscribed";

export function browserSupportsPush(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export async function getPushStatus(): Promise<PushStatus> {
  if (!browserSupportsPush()) return "unsupported";
  const key = await getPushPublicKey().catch(() => null);
  if (!key?.configured || !key.public_key) return "unconfigured";
  if (Notification.permission === "denied") return "blocked";
  const registration = await registerCrowscapServiceWorker();
  const subscription = await registration.pushManager.getSubscription();
  return subscription ? "subscribed" : "ready";
}

export async function subscribeToPush(): Promise<PushStatus> {
  if (!browserSupportsPush()) return "unsupported";
  const key = await getPushPublicKey();
  if (!key.configured || !key.public_key) return "unconfigured";

  if (Notification.permission === "denied") return "blocked";
  if (Notification.permission !== "granted") {
    const permission = await Notification.requestPermission();
    if (permission === "denied") return "blocked";
    if (permission !== "granted") return "ready";
  }

  const registration = await registerCrowscapServiceWorker();
  const existing = await registration.pushManager.getSubscription();
  const subscription =
    existing ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(key.public_key),
    }));

  await savePushSubscription(subscription.toJSON());
  return "subscribed";
}

export async function unsubscribeFromPush(): Promise<PushStatus> {
  if (!browserSupportsPush()) return "unsupported";
  const registration = await navigator.serviceWorker.getRegistration();
  const subscription = await registration?.pushManager.getSubscription();
  if (subscription?.endpoint) {
    await removePushSubscription(subscription.endpoint).catch(() => null);
    await subscription.unsubscribe();
  }
  return getPushStatus();
}

export async function registerCrowscapServiceWorker(): Promise<ServiceWorkerRegistration> {
  return navigator.serviceWorker.register("/sw.js", {
    scope: "/",
  });
}

export function connectNotificationStream(
  onEvent: (event: NotificationEvent) => void,
  onError?: () => void,
): () => void {
  if (typeof window === "undefined" || typeof EventSource === "undefined") {
    return () => undefined;
  }

  const source = new EventSource("/api/notifications/stream");
  const handleEvent = (message: MessageEvent<string>) => {
    try {
      const parsed = JSON.parse(message.data) as NotificationEvent;
      onEvent(parsed);
    } catch {
      // Ignore malformed stream events. The next heartbeat will reconnect state.
    }
  };

  source.addEventListener("reminder_due", handleEvent);
  source.addEventListener("recall_due", handleEvent);
  source.onerror = () => {
    onError?.();
  };

  return () => {
    source.close();
  };
}

export async function showForegroundNotification(
  event: NotificationEvent,
): Promise<void> {
  if (!browserSupportsPush()) return;
  if (Notification.permission !== "granted") return;
  if (document.visibilityState !== "hidden") return;

  const registration = await navigator.serviceWorker.getRegistration();
  await registration?.showNotification(event.title, {
    body: event.body,
    tag: event.event_key,
    data: { url: event.url },
    icon: "/icons/crowscap-icon.svg",
    badge: "/icons/crowscap-icon.svg",
  });
}

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const buffer = new ArrayBuffer(rawData.length);
  const outputArray = new Uint8Array(buffer);
  for (let index = 0; index < rawData.length; index += 1) {
    outputArray[index] = rawData.charCodeAt(index);
  }
  return buffer;
}
