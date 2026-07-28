import { useEffect, useRef } from "react";
import { useRouter } from "expo-router";
import {
  canUseNativeNotifications,
  getNotificationsModule,
  requestPushPermissions,
  getCurrentNotificationEvent,
  triggerLocalPushNotification,
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

    const checkNotification = async () => {
      const event = await getCurrentNotificationEvent();
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

    checkNotification();
    const interval = setInterval(checkNotification, 120_000); // Check every 2 min

    return () => {
      responseSubscription?.remove();
      clearInterval(interval);
    };
  }, [enabled, router]);
}
