import { useEffect } from "react";
import { useRouter } from "expo-router";

import { completeReminder } from "@/api/recalls";
import {
  canUseNativeNotifications,
  getNotificationsModule,
  registerNativePushToken,
  requestPushPermissions,
  setupNotificationChannels,
} from "@/utils/notifications";

export function useNotifications(enabled = true) {
  const router = useRouter();

  useEffect(() => {
    if (!enabled) return;
    if (!canUseNativeNotifications()) return;

    const Notifications = getNotificationsModule();
    if (!Notifications) return;

    requestPushPermissions().catch(() => null);
    registerNativePushToken().catch(() => null);
    setupNotificationChannels().catch(() => null);

    const autoPromptTimer = setTimeout(async () => {
      try {
        const notif = getNotificationsModule();
        if (!notif) return;
        const { status } = await notif.getPermissionsAsync();
        if (status !== "granted") {
          await requestPushPermissions();
          await registerNativePushToken();
        }
      } catch {}
    }, 60_000);

    let responseSubscription: { remove: () => void } | null = null;

    try {
      responseSubscription = Notifications.addNotificationResponseReceivedListener(
        async (response) => {
          const actionId = response.actionIdentifier;
          const data = response.notification.request.content.data;
          const reminderId = typeof data?.reminderId === "string" ? data.reminderId : null;
          const url = typeof data?.url === "string" ? data.url : "";

          if (actionId === "MARK_DONE" && reminderId) {
            try {
              await completeReminder(reminderId);
            } catch {}
            return;
          }

          if (actionId === "READ_MORE" || actionId === Notifications.DEFAULT_ACTION_IDENTIFIER) {
            if (url === "/recall" || url.startsWith("/recall") || url.includes("recall")) {
              router.push("/(tabs)/recall");
            } else {
              router.push("/(tabs)/recall");
            }
          }
        },
      );
    } catch {
      // Native notification listeners are unavailable in Expo Go and some simulators.
    }

    return () => {
      clearTimeout(autoPromptTimer);
      responseSubscription?.remove();
    };
  }, [enabled, router]);
}
