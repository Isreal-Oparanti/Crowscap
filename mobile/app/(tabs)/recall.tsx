import { View, Text, StyleSheet } from "react-native";
import { tokens } from "@/theme/tokens";

// TODO: Implement Recall screen — Phase 2
export default function RecallScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.placeholder}>Recall</Text>
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
