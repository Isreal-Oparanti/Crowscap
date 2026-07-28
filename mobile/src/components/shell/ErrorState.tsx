import { View, Text, StyleSheet } from "react-native";
import { tokens } from "@/theme/tokens";

export function ErrorState({ message }: { message: string }) {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.colors.background,
    paddingHorizontal: tokens.spacing[6],
  },
  text: {
    fontSize: tokens.fontSize.base,
    color: tokens.colors.danger,
    textAlign: "center",
    lineHeight: tokens.lineHeight.normal,
  },
});
