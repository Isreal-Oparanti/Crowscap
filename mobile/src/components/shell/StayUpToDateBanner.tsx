import { useState, useEffect, useCallback } from "react";

import { View, Text, StyleSheet, Switch, Alert, Linking } from "react-native";
import { useFocusEffect } from "expo-router";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import { getNotificationsModule, requestPushPermissions } from "@/utils/notifications";

export function StayUpToDateBanner() {
  const [permissionGranted, setPermissionGranted] = useState<boolean>(false);
  const [checked, setChecked] = useState<boolean>(false);

  const checkStatus = useCallback(async () => {
    const Notifications = getNotificationsModule();
    if (!Notifications) {
      setPermissionGranted(false);
      setChecked(true);
      return;
    }
    try {
      const { status } = await Notifications.getPermissionsAsync();
      setPermissionGranted(status === "granted");
    } catch {
      setPermissionGranted(false);
    } finally {
      setChecked(true);
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  useFocusEffect(
    useCallback(() => {
      checkStatus();
    }, [checkStatus])
  );


  const handleToggle = async () => {
    const granted = await requestPushPermissions();
    if (granted) {
      setPermissionGranted(true);
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

  if (!checked || permissionGranted) {
    return null;
  }


  return (
    <View style={styles.banner}>
      <View style={styles.left}>
        <Text style={styles.title}>Stay up to date</Text>
        <Text style={styles.sub}>
          Turn on notifications to know right away when you have due recalls, reminders, and memory nudges.
        </Text>
      </View>
      <Switch
        value={false}
        onValueChange={handleToggle}
        trackColor={{ false: "#d0d4d8", true: "#2d7058" }}
        thumbColor="#ffffff"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#f2f6f4",
    borderRadius: 16,
    padding: 16,
    marginHorizontal: tokens.spacing[5],
    marginBottom: 16,
    gap: 12,
  },
  left: {
    flex: 1,
    gap: 4,
  },
  title: {
    fontSize: 15,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  sub: {
    fontSize: 12,
    lineHeight: 17,
    fontFamily: fontFamily.medium,
    color: "#5c6064",
  },
});
