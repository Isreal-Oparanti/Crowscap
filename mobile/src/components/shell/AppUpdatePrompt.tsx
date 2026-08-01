import { useCallback, useEffect, useState } from "react";
import { AppState, Linking, Pressable, StyleSheet, Text, View } from "react-native";

import {
  checkNativeAndroidUpdate,
  checkOtaUpdate,
  type NativeUpdateInfo,
} from "@/utils/updates";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import { Icons } from "@/components/ui/Icon";

type PromptState =
  | { type: "none" }
  | { type: "ota"; reload: () => Promise<void> }
  | { type: "native"; update: NativeUpdateInfo };

export function AppUpdatePrompt() {
  const [prompt, setPrompt] = useState<PromptState>({ type: "none" });
  const [dismissedKey, setDismissedKey] = useState<string | null>(null);

  const checkForUpdates = useCallback(async () => {
    const nativeUpdate = await checkNativeAndroidUpdate();

    if (nativeUpdate.available) {
      const key = `native:${nativeUpdate.update.latestVersionCode}`;
      if (dismissedKey !== key) {
        setPrompt({ type: "native", update: nativeUpdate.update });
      }
      return;
    }

    const otaUpdate = await checkOtaUpdate();

    if (otaUpdate.available && dismissedKey !== "ota") {
      setPrompt({ type: "ota", reload: otaUpdate.reload });
    }
  }, [dismissedKey]);

  useEffect(() => {
    checkForUpdates();
  }, [checkForUpdates]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active") {
        checkForUpdates();
      }
    });

    return () => subscription.remove();
  }, [checkForUpdates]);

  if (prompt.type === "none") {
    return null;
  }

  const isNative = prompt.type === "native";
  const title = isNative ? "New app version ready" : "Update ready";
  const body = isNative
    ? prompt.update.notes || "Install the latest Android build to get native fixes and notification updates."
    : "Crowscap has downloaded improvements. Restart when you are ready.";

  const handlePrimary = () => {
    if (prompt.type === "native") {
      Linking.openURL(prompt.update.apkUrl);
      return;
    }

    prompt.reload();
  };

  const handleDismiss = () => {
    if (prompt.type === "native") {
      setDismissedKey(`native:${prompt.update.latestVersionCode}`);
    } else {
      setDismissedKey("ota");
    }
    setPrompt({ type: "none" });
  };

  return (
    <View pointerEvents="box-none" style={styles.wrap}>
      <View style={styles.card}>
        <View style={styles.iconBox}>
          <Icons.ArrowUp size={17} color={tokens.colors.text} strokeWidth={2.4} />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.body} numberOfLines={2}>
            {body}
          </Text>
        </View>
        <View style={styles.actions}>
          <Pressable onPress={handlePrimary} style={styles.primary}>
            <Text style={styles.primaryText}>{isNative ? "Download" : "Restart"}</Text>
          </Pressable>
          <Pressable onPress={handleDismiss} hitSlop={10} style={styles.close}>
            <Icons.X size={18} color={tokens.colors.textMuted} strokeWidth={2.2} />
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: 16,
    right: 16,
    bottom: 22,
    zIndex: 50,
  },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    backgroundColor: "#ffffff",
    padding: 12,
    shadowColor: "#000000",
    shadowOpacity: 0.12,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 8,
  },
  iconBox: {
    width: 38,
    height: 38,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.colors.surface,
  },
  copy: {
    flex: 1,
    gap: 2,
  },
  title: {
    fontFamily: fontFamily.extrabold,
    fontSize: 14,
    color: tokens.colors.text,
  },
  body: {
    fontFamily: fontFamily.medium,
    fontSize: 12,
    lineHeight: 17,
    color: tokens.colors.textMuted,
  },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  primary: {
    borderRadius: 999,
    backgroundColor: tokens.colors.text,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  primaryText: {
    fontFamily: fontFamily.extrabold,
    fontSize: 11,
    color: "#ffffff",
  },
  close: {
    width: 28,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
  },
});
