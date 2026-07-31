import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  Switch,
  Alert,
  Linking,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Icons } from "@/components/ui/Icon";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import {
  getNotificationsModule,
  requestPushPermissions,
  scheduleLocalNotification,
} from "@/utils/notifications";

const NOTIF_PREFS_KEY = "@crowscap_notification_preferences_v1";

export interface NotificationPreferences {
  dueReminders: boolean;
  recallNudges: boolean;
  extractionCompleted: boolean;
  pushNotifications: boolean;
  soundVibration: boolean;
}

const defaultPrefs: NotificationPreferences = {
  dueReminders: true,
  recallNudges: true,
  extractionCompleted: true,
  pushNotifications: true,
  soundVibration: true,
};

export default function NotificationSettingsScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const [prefs, setPrefs] = useState<NotificationPreferences>(defaultPrefs);
  const [systemPermissionGranted, setSystemPermissionGranted] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);

  const checkPermissionStatus = useCallback(async () => {
    const Notifications = getNotificationsModule();
    if (!Notifications) {
      setSystemPermissionGranted(false);
      return;
    }
    try {
      const { status } = await Notifications.getPermissionsAsync();
      setSystemPermissionGranted(status === "granted");
    } catch {
      setSystemPermissionGranted(false);
    }
  }, []);

  useEffect(() => {
    checkPermissionStatus();
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(NOTIF_PREFS_KEY);
        if (raw) {
          setPrefs({ ...defaultPrefs, ...JSON.parse(raw) });
        }
      } catch {
      } finally {
        setLoading(false);
      }
    })();
  }, [checkPermissionStatus]);


  useFocusEffect(
    useCallback(() => {
      checkPermissionStatus();
    }, [checkPermissionStatus])
  );

  const handleEnableSystemNotifications = async () => {
    const granted = await requestPushPermissions();
    if (granted) {
      setSystemPermissionGranted(true);
    } else {
      Alert.alert(
        "Notifications Disabled",
        "Notification permissions are turned off on your device. Would you like to open system settings to turn them on?",
        [
          { text: "Cancel", style: "cancel" },
          { text: "Open Settings", onPress: () => Linking.openSettings() },
        ]
      );
    }
  };

  const updatePref = async (key: keyof NotificationPreferences, value: boolean) => {
    const updated = { ...prefs, [key]: value };
    setPrefs(updated);
    try {
      await AsyncStorage.setItem(NOTIF_PREFS_KEY, JSON.stringify(updated));
    } catch {}
  };

  return (
    <View style={styles.root}>
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerRow}>
          <Pressable onPress={() => router.back()} style={styles.backButton} hitSlop={8}>
            <Icons.ArrowLeft size={20} color={tokens.colors.text} />
          </Pressable>
          <Text style={styles.headerTitle}>Notifications</Text>
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: insets.bottom + 32 },
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* Top Banner Card: Only shown if system notification permission is NOT granted */}
        {!systemPermissionGranted ? (
          <View style={styles.topCard}>
            <View style={styles.topCardLeft}>
              <Text style={styles.topCardTitle}>Stay up to date</Text>
              <Text style={styles.topCardSub}>
                Turn on notifications to know right away when you have due recalls, reminders, and memory nudges.
              </Text>
            </View>
            <Switch
              value={false}
              onValueChange={handleEnableSystemNotifications}
              trackColor={{ false: "#d0d4d8", true: "#2d7058" }}
              thumbColor="#ffffff"
            />
          </View>
        ) : null}


        {/* Section: Activity */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ACTIVITY</Text>
          <View style={styles.group}>
            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.Clock3 size={18} color="#4d5154" />
                <View style={styles.rowTextWrap}>
                  <Text style={styles.rowTitle}>Due reminders</Text>
                  <Text style={styles.rowSub}>Alerts when a saved reminder is ready</Text>
                </View>
              </View>
              <Switch
                value={prefs.dueReminders}
                onValueChange={(val) => updatePref("dueReminders", val)}
                trackColor={{ false: "#e0e2e5", true: "#357a62" }}
                thumbColor="#ffffff"
              />
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.BookOpenCheck size={18} color="#4d5154" />

                <View style={styles.rowTextWrap}>
                  <Text style={styles.rowTitle}>Recall nudges</Text>
                  <Text style={styles.rowSub}>Spaced repetition review notifications</Text>
                </View>
              </View>
              <Switch
                value={prefs.recallNudges}
                onValueChange={(val) => updatePref("recallNudges", val)}
                trackColor={{ false: "#e0e2e5", true: "#357a62" }}
                thumbColor="#ffffff"
              />
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.FileText size={18} color="#4d5154" />
                <View style={styles.rowTextWrap}>
                  <Text style={styles.rowTitle}>Extraction completed</Text>
                  <Text style={styles.rowSub}>Alerts when long link or PDF processing finishes</Text>
                </View>
              </View>
              <Switch
                value={prefs.extractionCompleted}
                onValueChange={(val) => updatePref("extractionCompleted", val)}
                trackColor={{ false: "#e0e2e5", true: "#357a62" }}
                thumbColor="#ffffff"
              />
            </View>
          </View>
        </View>

        {/* Section: Delivery Method */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>DELIVERY METHOD</Text>
          <View style={styles.group}>
            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.Bell size={18} color="#4d5154" />
                <View style={styles.rowTextWrap}>
                  <Text style={styles.rowTitle}>Push notifications</Text>
                  <Text style={styles.rowSub}>System notifications on this device</Text>
                </View>
              </View>
              <Switch
                value={prefs.pushNotifications}
                onValueChange={(val) => updatePref("pushNotifications", val)}
                trackColor={{ false: "#e0e2e5", true: "#357a62" }}
                thumbColor="#ffffff"
              />
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.Volume2 size={18} color="#4d5154" />
                <View style={styles.rowTextWrap}>
                  <Text style={styles.rowTitle}>Sound & vibration</Text>
                  <Text style={styles.rowSub}>Play audio chime and vibrate on alert</Text>
                </View>
              </View>
              <Switch
                value={prefs.soundVibration}
                onValueChange={(val) => updatePref("soundVibration", val)}
                trackColor={{ false: "#e0e2e5", true: "#357a62" }}
                thumbColor="#ffffff"
              />
            </View>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  header: {
    paddingHorizontal: tokens.spacing[5],
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e7e8e9",
    backgroundColor: "#ffffff",
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  headerTitle: {
    fontSize: 18,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },

  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: tokens.spacing[5],
    paddingTop: tokens.spacing[5],
    gap: 24,
  },

  topCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",

    backgroundColor: "#f2f6f4",
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  topCardLeft: {
    flex: 1,
    gap: 4,
  },
  topCardTitle: {
    fontSize: 15,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  topCardSub: {
    fontSize: 12,
    lineHeight: 17,
    fontFamily: fontFamily.medium,
    color: "#5c6064",
  },

  testButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#c3e0d2",
    backgroundColor: "#f4f9f6",
  },
  testButtonText: {
    fontSize: 13,
    fontFamily: fontFamily.bold,
    color: "#2d7058",
  },

  section: {
    gap: 8,
  },
  sectionLabel: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#8a8d90",
    letterSpacing: 0.5,
  },
  group: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 14,
    backgroundColor: "#ffffff",
    paddingHorizontal: 16,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 14,
  },
  rowLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    flex: 1,
    marginRight: 8,
  },
  rowTextWrap: {
    flex: 1,
    gap: 2,
  },
  rowTitle: {
    fontSize: 13.5,
    fontFamily: fontFamily.bold,
    color: tokens.colors.text,
  },
  rowSub: {
    fontSize: 11.5,
    fontFamily: fontFamily.medium,
    color: "#787c80",
  },
  divider: {
    height: 1,
    backgroundColor: "#e8eaec",
  },
});
