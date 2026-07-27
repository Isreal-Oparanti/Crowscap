import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { tokens } from "@/theme/tokens";

// TODO: Implement memory detail view — Phase 4
export default function MemoryDetailModal() {
  const { id } = useLocalSearchParams<{ id: string }>();

  return (
    <View style={styles.container}>
      <Text style={styles.placeholder}>Memory {id}</Text>
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
