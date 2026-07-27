import { View, Text, StyleSheet } from "react-native";
import { tokens } from "@/theme/tokens";

// TODO: Implement Search screen — Phase 2
export default function SearchScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.placeholder}>Search</Text>
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
