import { useEffect, useRef } from "react";
import { useRouter } from "expo-router";
import { backendUrl, getAuthToken } from "@/api/client";
import {
  canUseNativeNotifications,
  getNotificationsModule,
  requestPushPermissions,
  getCurrentNotificationEvent,
  triggerLocalPushNotification,
  type CurrentNotificationEvent,
} from "@/utils/notifications";

export function useNotifications(enabled = true) {
  const router = useRouter();
  const lastEventKey = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    if (!canUseNativeNotifications()) return;

    const Notifications = getNotificationsModule();
    if (!Notifications) return;

    requestPushPermissions().catch(() => null);

    let responseSubscription: { remove: () => void } | null = null;
    try {
      responseSubscription = Notifications.addNotificationResponseReceivedListener(
        (response) => {
          const data = response.notification.request.content.data;
          const url = typeof data?.url === "string" ? data.url : "";
          if (url === "/recall" || url.startsWith("/recall")) {
            router.push("/(tabs)/recall");
          }
        }
      );
    } catch {
      // Ignore if native listener initialization is unavailable.
    }

    const handleEvent = async (event: CurrentNotificationEvent) => {
      if (
        event &&
        event.event_type !== "heartbeat" &&
        event.due_count > 0 &&
        event.event_key !== lastEventKey.current
      ) {
        lastEventKey.current = event.event_key;
        await triggerLocalPushNotification(event.title, event.body);
      }
    };

    // Initial event check on app mount (single call, non-polling)
    getCurrentNotificationEvent().then((evt) => {
      if (evt) handleEvent(evt);
    });

    // Establish persistent Server-Sent Events (SSE) connection — zero DB polling!
    const controller = new AbortController();
    const connectSSE = async () => {
      const token = await getAuthToken();
      if (!token) return;

      try {
        const streamUrl = `${backendUrl}/api/v1/notifications/stream`;
        const res = await fetch(streamUrl, {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "text/event-stream",
          },
          signal: controller.signal,
        });

        if (!res.ok || !res.body) return;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!controller.signal.aborted) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() ?? "";

          for (const block of blocks) {
            const lines = block.split("\n");
            let eventType = "";
            let dataStr = "";

            for (const line of lines) {
              if (line.startsWith("event:")) eventType = line.replace("event:", "").trim();
              if (line.startsWith("data:")) dataStr = line.replace("data:", "").trim();
            }

            if (dataStr && eventType && eventType !== "connected" && eventType !== "heartbeat") {
              try {
                const parsed: CurrentNotificationEvent = JSON.parse(dataStr);
                handleEvent(parsed);
              } catch {}
            }
          }
        }
      } catch {}
    };

    connectSSE();

    return () => {
      controller.abort();
      responseSubscription?.remove();
    };
  }, [enabled, router]);
}

