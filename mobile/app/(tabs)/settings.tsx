import { View, Text, StyleSheet } from "react-native";
import { tokens } from "@/theme/tokens";

// TODO: Implement Settings screen — Phase 4
export default function SettingsScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.placeholder}>Settings</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: tokens.colors.background,
    alignItems: "center",
    justifyContent: "center",
  },
  placeholder: {
    color: tokens.colors.textMuted,
    fontSize: 14,
  },
});
