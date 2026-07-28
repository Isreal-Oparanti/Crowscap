import { View, ActivityIndicator, StyleSheet } from "react-native";
import { tokens } from "@/theme/tokens";

export function LoadingState() {
  return (
    <View style={styles.container}>
      <ActivityIndicator color={tokens.colors.text} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.colors.background,
  },
});
