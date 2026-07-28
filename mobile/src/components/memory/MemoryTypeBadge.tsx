import { View, Text, StyleSheet } from "react-native";
import type { MemoryType } from "@/types/api";
import { memoryTypeLabel } from "@/utils/format";

const TYPE_STYLES: Record<string, { bg: string; text: string }> = {
  principle: { bg: "#eef4f7", text: "#2b5b7a" },
  claim: { bg: "#f4f0f7", text: "#5d357a" },
  warning: { bg: "#f8ebec", text: "#9b4c51" },
  action: { bg: "#eaf4ef", text: "#2d7058" },
  question: { bg: "#f7f7ee", text: "#757025" },
  definition: { bg: "#f0f4f8", text: "#2d4b68" },
  example: { bg: "#f7f2ea", text: "#7a5c2b" },
  quote: { bg: "#f0f2f3", text: "#4d5154" },
  reference: { bg: "#f0f2f3", text: "#4d5154" },
  intention: { bg: "#f7eef5", text: "#7a2b6b" },
};

export function MemoryTypeBadge({ type }: { type: MemoryType }) {
  const style = TYPE_STYLES[type] ?? { bg: "#f1f2f3", text: "#4d5154" };

  return (
    <View style={[styles.badge, { backgroundColor: style.bg }]}>
      <Text style={[styles.badgeText, { color: style.text }]}>
        {memoryTypeLabel(type)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: "flex-start",
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.3,
  },
});
