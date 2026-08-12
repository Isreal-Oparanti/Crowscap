import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Icons } from "@/components/ui/Icon";
import { useAuth } from "@/hooks/useAuth";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";

import { useState } from "react";
import { checkNativeAndroidUpdate, checkOtaUpdate } from "@/utils/updates";
import { learnPreferencesNow } from "@/api/chat";

export default function SettingsScreen() {
  const insets = useSafeAreaInsets();
  const { session, signOut } = useAuth();
  const router = useRouter();
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateStatusText, setUpdateStatusText] = useState("v1.0.0");
  const [learning, setLearning] = useState(false);
  const [learnMessage, setLearnMessage] = useState<string | null>(null);

  const handleLearnNow = async () => {
    if (learning) return;
    setLearning(true);
    setLearnMessage(null);
    try {
      const res = await learnPreferencesNow();
      setLearnMessage(
        res.updates.length > 0
          ? `Learned ${res.updates.length} pattern(s) from your context!`
          : "Preferences are already up to date."
      );
    } catch {
      setLearnMessage("Could not update preferences.");
    } finally {
      setLearning(false);
    }
  };

  const handleCheckForUpdates = async () => {
    if (checkingUpdate) return;
    setCheckingUpdate(true);
    try {
      const nativeRes = await checkNativeAndroidUpdate();
      if (nativeRes.available) {
        setUpdateStatusText("Update ready");
        Alert.alert(
          "Update Available",
          "A new version of Crowscap is available. Would you like to download it?",
          [
            { text: "Later", style: "cancel" },
            {
              text: "Download",
              onPress: () => {
                const { Linking } = require("react-native");
                Linking.openURL(nativeRes.update.apkUrl);
              },
            },
          ]
        );
        return;
      }

      const otaRes = await checkOtaUpdate();
      if (otaRes.available) {
        setUpdateStatusText("Restart ready");
        Alert.alert(
          "Update Ready",
          "A new update has been downloaded. Restart app now?",
          [
            { text: "Later", style: "cancel" },
            {
              text: "Restart Now",
              onPress: () => {
                otaRes.reload();
              },
            },
          ]
        );
        return;
      }

      setUpdateStatusText("Up to date");
      Alert.alert("Up to Date", "Crowscap is up to date with the latest features.");
    } catch {
      setUpdateStatusText("Up to date");
    } finally {
      setCheckingUpdate(false);
    }
  };

  const handleSignOut = async () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out of Crowscap?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await signOut();
          router.replace("/sign-in");
        },
      },
    ]);
  };

  const displayName = session?.name ?? session?.email?.split("@")[0] ?? "Crowscap user";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  return (
    <View style={styles.root}>
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerRow}>
          <Pressable onPress={() => router.back()} style={styles.backButton} hitSlop={8}>
            <Icons.ArrowLeft size={20} color={tokens.colors.text} />
          </Pressable>
          <View>
            <Text style={styles.headerTitle}>Settings</Text>
            <Text style={styles.headerSub}>Account preferences & profile</Text>
          </View>
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
        {/* Profile Card */}
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initials || "C"}</Text>
          </View>
          <View style={styles.profileMeta}>
            <Text style={styles.displayName}>{displayName}</Text>
            <Text style={styles.emailText}>{session?.email ?? "Private account"}</Text>
          </View>
        </View>

        {/* Notifications */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>NOTIFICATIONS & PREFERENCES</Text>
          <View style={styles.settingsGroup}>
            <Pressable
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              onPress={() => router.push("/notifications-settings")}
            >
              <View style={styles.rowLeft}>
                <Icons.Bell size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Notification preferences</Text>
              </View>
              <Icons.ChevronRight size={16} color="#8a8d90" />
            </Pressable>
          </View>
        </View>

        {/* Intelligence Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>MEMORY AGENT ADAPTATION</Text>
          <View style={styles.settingsGroup}>
            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.MessageCircle size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Answer style</Text>
              </View>
              <View style={styles.valueBadge}>
                <Text style={styles.valueText}>Concise</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.Shield size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Evidence strictness</Text>
              </View>
              <View style={styles.valueBadge}>
                <Text style={styles.valueText}>Balanced</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.HelpCircle size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Challenge style</Text>
              </View>
              <View style={styles.valueBadge}>
                <Text style={styles.valueText}>Direct</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.Sparkles size={16} color="#2d7058" />
                <Text style={styles.rowTitle}>Adapt agent to recent thoughts</Text>
              </View>
              <Pressable
                style={({ pressed }) => [styles.adaptBadge, pressed && { opacity: 0.7 }]}
                onPress={handleLearnNow}
                disabled={learning}
              >
                {learning ? (
                  <ActivityIndicator size="small" color="#2d7058" />
                ) : (
                  <Text style={styles.adaptBadgeText}>Adapt Now</Text>
                )}
              </Pressable>
            </View>
          </View>
          {learnMessage ? (
            <Text style={styles.learnMessageText}>{learnMessage}</Text>
          ) : null}
        </View>

        {/* App Updates & System */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>APP UPDATES & SYSTEM</Text>
          <View style={styles.settingsGroup}>
            <Pressable
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              onPress={handleCheckForUpdates}
              disabled={checkingUpdate}
            >
              <View style={styles.rowLeft}>
                <Icons.RefreshCw size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Check for updates</Text>
              </View>
              <View style={styles.valueBadge}>
                {checkingUpdate ? (
                  <ActivityIndicator size="small" color="#111111" />
                ) : (
                  <Text style={styles.valueText}>{updateStatusText}</Text>
                )}
              </View>
            </Pressable>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Icons.Info size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Version</Text>
              </View>
              <View style={styles.valueBadge}>
                <Text style={styles.valueText}>v1.0.0</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Sign Out Button */}
        <Pressable
          style={({ pressed }) => [
            styles.signOutBtn,
            pressed && { opacity: 0.8 },
          ]}
          onPress={handleSignOut}
        >
          <Icons.LogOut size={16} color="#9b4c51" />
          <Text style={styles.signOutText}>Sign Out</Text>
        </Pressable>
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
    letterSpacing: 0,
  },
  headerSub: {
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: tokens.colors.textMuted,
    marginTop: 2,
  },

  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: tokens.spacing[5],
    paddingTop: tokens.spacing[5],
    gap: tokens.spacing[6],
  },

  profileCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[4],
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 16,
    padding: tokens.spacing[4],
    backgroundColor: "#fafafa",
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#dfe7e3",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    fontSize: 15,
    fontFamily: fontFamily.extrabold,
    color: "#275d4b",
  },
  profileMeta: {
    flex: 1,
    gap: 2,
  },
  displayName: {
    fontSize: 15,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  emailText: {
    fontSize: 12,
    fontFamily: fontFamily.medium,
    color: "#787c80",
  },

  section: {
    gap: tokens.spacing[2],
  },
  sectionLabel: {
    fontSize: 10,
    fontFamily: fontFamily.extrabold,
    color: "#8a8d90",
    letterSpacing: 0,
  },
  settingsGroup: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 14,
    backgroundColor: "#ffffff",
    paddingHorizontal: tokens.spacing[4],
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
    gap: 10,
  },
  rowTitle: {
    fontSize: 13,
    fontFamily: fontFamily.semibold,
    color: tokens.colors.text,
  },
  valueBadge: {
    backgroundColor: "#f2f3f4",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  valueText: {
    fontSize: 11,
    fontFamily: fontFamily.bold,
    color: "#4d5154",
  },
  statusGreen: {
    fontSize: 12,
    fontFamily: fontFamily.extrabold,
    color: "#2d7058",
  },
  rowSubText: {
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: "#8a8d90",
  },
  divider: {
    height: 1,
    backgroundColor: "#e8eaec",
  },

  signOutBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#f5d0d0",
    backgroundColor: "#fff5f5",
    marginTop: 8,
  },
  signOutText: {
    fontSize: 13,
    fontFamily: fontFamily.extrabold,
    color: "#9b4c51",
  },
  adaptBadge: {
    backgroundColor: "#eaf3ee",
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  adaptBadgeText: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#2d7058",
  },
  learnMessageText: {
    fontSize: 11,
    fontFamily: fontFamily.semibold,
    color: "#2d7058",
    marginTop: 6,
    paddingHorizontal: 4,
  },
  versionText: {
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: "#b4b7b9",
    textAlign: "center",
    marginTop: 4,
  },
});
