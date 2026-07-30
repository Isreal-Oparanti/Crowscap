import { View, Text, StyleSheet } from "react-native";
import type { Confidence } from "@/types/api";
import { fontFamily } from "@/theme/typography";

const CONFIDENCE_COLORS: Record<Confidence, string> = {
  high: "#2d7058",
  medium: "#b07030",
  low: "#9b4c51",
  unknown: "#b4b7b9",
};

export function ConfidencePill({ confidence }: { confidence: Confidence }) {
  const dotColor = CONFIDENCE_COLORS[confidence] ?? "#b4b7b9";

  return (
    <View style={styles.container}>
      <View style={[styles.dot, { backgroundColor: dotColor }]} />
      <Text style={styles.label}>{confidence} confidence</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  label: {
    fontSize: 10,
    fontFamily: fontFamily.semibold,
    color: "#8a8d90",
  },
});
