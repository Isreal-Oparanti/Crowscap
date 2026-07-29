import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  Alert,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useAuth } from "@/hooks/useAuth";
import { tokens } from "@/theme/tokens";

export default function SettingsScreen() {
  const insets = useSafeAreaInsets();
  const { session, signOut } = useAuth();
  const router = useRouter();

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
            <Feather name="arrow-left" size={20} color={tokens.colors.text} />
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

        {/* Intelligence Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>MEMORY AGENT ADAPTATION</Text>
          <View style={styles.settingsGroup}>
            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Feather name="message-square" size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Answer style</Text>
              </View>
              <View style={styles.valueBadge}>
                <Text style={styles.valueText}>Concise</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Feather name="shield" size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Evidence strictness</Text>
              </View>
              <View style={styles.valueBadge}>
                <Text style={styles.valueText}>Balanced</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Feather name="help-circle" size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Challenge style</Text>
              </View>
              <View style={styles.valueBadge}>
                <Text style={styles.valueText}>Direct</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Security & Data */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>SECURITY & DATA</Text>
          <View style={styles.settingsGroup}>
            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Feather name="lock" size={16} color="#2d7058" />
                <Text style={styles.rowTitle}>User data isolation</Text>
              </View>
              <Text style={styles.statusGreen}>Active</Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <View style={styles.rowLeft}>
                <Feather name="server" size={16} color="#4d5154" />
                <Text style={styles.rowTitle}>Backend service</Text>
              </View>
              <Text style={styles.rowSubText}>api.crowscap.xyz</Text>
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
          <Feather name="log-out" size={16} color="#9b4c51" />
          <Text style={styles.signOutText}>Sign Out</Text>
        </Pressable>

        <Text style={styles.versionText}>Crowscap Mobile v1.0.0 (Expo SDK 54)</Text>
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
    fontWeight: "800",
    color: tokens.colors.text,
    letterSpacing: -0.3,
  },
  headerSub: {
    fontSize: 11,
    fontWeight: "500",
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
    fontWeight: "800",
    color: "#275d4b",
  },
  profileMeta: {
    flex: 1,
    gap: 2,
  },
  displayName: {
    fontSize: 15,
    fontWeight: "800",
    color: tokens.colors.text,
  },
  emailText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#787c80",
  },

  section: {
    gap: tokens.spacing[2],
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: "#8a8d90",
    letterSpacing: 0.6,
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
    fontWeight: "600",
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
    fontWeight: "700",
    color: "#4d5154",
  },
  statusGreen: {
    fontSize: 12,
    fontWeight: "800",
    color: "#2d7058",
  },
  rowSubText: {
    fontSize: 11,
    fontWeight: "500",
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
    fontWeight: "800",
    color: "#9b4c51",
  },
  versionText: {
    fontSize: 11,
    fontWeight: "500",
    color: "#b4b7b9",
    textAlign: "center",
    marginTop: 4,
  },
});
