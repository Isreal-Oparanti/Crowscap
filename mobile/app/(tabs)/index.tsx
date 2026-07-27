import { View, Text, StyleSheet } from "react-native";
import { tokens } from "@/theme/tokens";

// TODO: Implement Chat screen — Phase 1
export default function ChatScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.placeholder}>Chat</Text>
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
