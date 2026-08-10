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
          const memoryId = typeof data?.memoryId === "string" ? data.memoryId : null;

          if (actionId === "MARK_DONE" && reminderId) {
            try {
              await completeReminder(reminderId);
            } catch {}
            return;
          }

          if (actionId === "READ_MORE" || actionId === Notifications.DEFAULT_ACTION_IDENTIFIER) {
            // Build the target URL with the specific memory/reminder ID so recall.tsx
            // can open and highlight the exact card that was notified
            if (memoryId) {
              router.push(`/(tabs)/recall?target_memory_id=${encodeURIComponent(memoryId)}` as never);
            } else if (reminderId) {
              router.push(`/(tabs)/recall?target_reminder_id=${encodeURIComponent(reminderId)}` as never);
            } else {
              router.push("/(tabs)/recall" as never);
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
