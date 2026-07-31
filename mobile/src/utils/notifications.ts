import Constants from "expo-constants";
import * as Device from "expo-device";
import { Platform } from "react-native";
import { apiRequest } from "@/api/client";

type NotificationsModule = typeof import("expo-notifications");
declare const require: (moduleName: string) => NotificationsModule;

let notificationsModule: NotificationsModule | null | undefined;
let isHandlerSet = false;

/** Check if running inside Expo Go */
export function isExpoGo() {
  return Constants.appOwnership === "expo";
}

/** Check if device is a physical hardware device */
export function isPhysicalDevice() {
  return Device.isDevice;
}

/** Retrieve expo-notifications module safely */
export function getNotificationsModule(): NotificationsModule | null {
  if (notificationsModule !== undefined) return notificationsModule;

  try {
    notificationsModule = require("expo-notifications");
  } catch {
    notificationsModule = null;
  }

  return notificationsModule;
}

export const REMINDER_CATEGORY_ID = "REMINDER_CATEGORY";

/** Build Android MAX importance notification channel, register categories & set foreground handler */
export async function setupNotificationChannels(): Promise<boolean> {
  if (isHandlerSet) return true;
  const Notifications = getNotificationsModule();
  if (!Notifications) return false;

  try {
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
      }),
    });

    // Register Category with Mark Done and Read More actions
    await Notifications.setNotificationCategoryAsync(REMINDER_CATEGORY_ID, [
      {
        identifier: "MARK_DONE",
        buttonTitle: "Mark done",
        options: {
          isAuthenticationRequired: false,
          isDestructive: false,
        },
      },
      {
        identifier: "READ_MORE",
        buttonTitle: "Read more",
        options: {
          isAuthenticationRequired: false,
          isDestructive: false,
        },
      },
    ]);

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "Crowscap Notifications",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#2d7058",
        sound: "default",
        enableVibrate: true,
        showBadge: true,
      });
    }

    isHandlerSet = true;
    return true;
  } catch {
    return false;
  }
}

export interface CurrentNotificationEvent {
  event_id: string;
  event_key: string;
  event_type: string;
  due_count: number;
  title: string;
  body: string;
  url: string;
  reminder_id: string | null;
  memory_id: string | null;
  notification_title?: string;
  notification_body?: string;
  created_at: string;
}

export interface CurrentNotificationResponse {
  event: CurrentNotificationEvent;
}

/** Request notification permissions and build Android channel */
export async function requestPushPermissions(): Promise<boolean> {
  const Notifications = getNotificationsModule();
  if (!Notifications) return false;

  await setupNotificationChannels();

  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    return finalStatus === "granted";
  } catch {
    return false;
  }
}

import AsyncStorage from "@react-native-async-storage/async-storage";

const REMINDER_STORAGE_KEY = "@crowscap_scheduled_reminders_v1";

interface ScheduledReminderMeta {
  notificationId: string;
  dueAt: string;
}

async function getScheduledReminderMap(): Promise<Record<string, ScheduledReminderMeta>> {
  try {
    const raw = await AsyncStorage.getItem(REMINDER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

async function saveScheduledReminderMap(map: Record<string, ScheduledReminderMeta>) {
  try {
    await AsyncStorage.setItem(REMINDER_STORAGE_KEY, JSON.stringify(map));
  } catch {}
}

/** Schedule or update an on-device local notification with stored identifier checking & deduplication */
export async function scheduleOrUpdateLocalReminder({
  reminderId,
  title,
  body,
  dueAt,
  memoryId,
  url = "/(tabs)/recall",
}: {
  reminderId: string;
  title: string;
  body: string;
  dueAt: string;
  memoryId?: string | null;
  url?: string;
}): Promise<string | null> {
  const Notifications = getNotificationsModule();
  if (!Notifications) return null;

  await setupNotificationChannels();

  const dueMs = new Date(dueAt).getTime();
  if (Number.isNaN(dueMs)) return null;

  const now = Date.now();
  const diffSeconds = Math.round((dueMs - now) / 1000);

  // If reminder is in the past, don't schedule on-device future trigger
  if (diffSeconds <= 0) return null;

  const map = await getScheduledReminderMap();
  const existing = map[reminderId];

  // 1. If already scheduled and due time HAS NOT changed, don't reschedule!
  if (existing && existing.dueAt === dueAt && existing.notificationId) {
    return existing.notificationId;
  }

  // 2. If due time changed or old identifier exists, cancel the old scheduled notification first!
  if (existing && existing.notificationId) {
    try {
      await Notifications.cancelScheduledNotificationAsync(existing.notificationId);
    } catch {}
  }

  // 3. Schedule new notification and capture the returned identifier!
  try {
    const notificationId = await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        sound: "default",
        categoryIdentifier: REMINDER_CATEGORY_ID,
        data: { url, reminderId, memoryId: memoryId || null },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
        seconds: diffSeconds,
        repeats: false,
      } as any,
    });

    map[reminderId] = { notificationId, dueAt };
    await saveScheduledReminderMap(map);

    return notificationId;
  } catch {
    return null;
  }
}

/** Schedule a simple local notification (e.g. 5s test button) */
export async function scheduleLocalNotification({
  title,
  body,
  url = "/(tabs)/recall",
  seconds,
}: {
  title: string;
  body: string;
  url?: string;
  seconds?: number;
}) {
  const Notifications = getNotificationsModule();
  if (!Notifications) return false;

  await setupNotificationChannels();

  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        sound: "default",
        categoryIdentifier: REMINDER_CATEGORY_ID,
        data: { url },
      },
      trigger: seconds && seconds > 0 ? ({ type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds, repeats: false } as any) : null,
    });
    return true;
  } catch {
    return false;
  }
}

/** Fetch current due notification event from backend */
export async function getCurrentNotificationEvent(): Promise<CurrentNotificationEvent | null> {
  try {
    const res = await apiRequest<CurrentNotificationResponse>("/notifications/current");
    return res.event;
  } catch {
    return null;
  }
}



