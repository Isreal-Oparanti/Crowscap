import Constants from "expo-constants";
import { Platform } from "react-native";
import { apiRequest } from "@/api/client";

type NotificationsModule = typeof import("expo-notifications");

declare const require: (moduleName: string) => NotificationsModule;

let notificationsModule: NotificationsModule | null | undefined;
let isHandlerSet = false;

export function canUseNativeNotifications() {
  return Constants.appOwnership !== "expo";
}

export function getNotificationsModule() {
  if (!canUseNativeNotifications()) return null;
  if (notificationsModule !== undefined) return notificationsModule;

  try {
    notificationsModule = require("expo-notifications");
  } catch {
    notificationsModule = null;
  }

  return notificationsModule;
}

function ensureNotificationHandler() {
  if (isHandlerSet) return;
  const Notifications = getNotificationsModule();
  if (!Notifications) return;

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
    isHandlerSet = true;
  } catch {
    // Native notifications are available only in a development or production build.
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
  created_at: string;
}

export interface CurrentNotificationResponse {
  event: CurrentNotificationEvent;
}

export async function requestPushPermissions(): Promise<boolean> {
  const Notifications = getNotificationsModule();
  if (!Notifications) return false;

  ensureNotificationHandler();

  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== "granted") return false;

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "default",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#2d7058",
      });
    }

    return true;
  } catch {
    return false;
  }
}

export async function getCurrentNotificationEvent(): Promise<CurrentNotificationEvent | null> {
  try {
    const res = await apiRequest<CurrentNotificationResponse>("/notifications/current");
    return res.event;
  } catch {
    return null;
  }
}

export async function triggerLocalPushNotification(title: string, body: string) {
  const Notifications = getNotificationsModule();
  if (!Notifications) return false;

  ensureNotificationHandler();

  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        sound: "default",
        data: { url: "/recall" },
      },
      trigger: null,
    });
    return true;
  } catch {
    return false;
  }
}
