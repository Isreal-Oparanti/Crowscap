import { View, Text, StyleSheet } from "react-native";
import type { MemoryRelation } from "@/types/api";
import { Icons } from "@/components/ui/Icon";
import { fontFamily } from "@/theme/typography";

const RELATION_LABELS: Record<string, string> = {
  confirms: "Agrees with something you saved",
  conflicts: "Disagrees with something you saved",
  tension: "Worth comparing with something you saved",
  extends: "Adds to something you saved",
  qualifies: "Adds an important condition",
};

export function RelationRow({ relation }: { relation: MemoryRelation }) {
  const label = RELATION_LABELS[relation.relationship_type] ?? "Connected memory";

  return (
    <View style={styles.container}>
      <Icons.GitMerge size={13} color="#8b5a1e" style={styles.icon} />
      <View style={styles.content}>
        <Text style={styles.label}>{label.toUpperCase()}</Text>
        {relation.explanation ? (
          <Text style={styles.explanation}>{relation.explanation}</Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    backgroundColor: "#fffbf2",
    borderWidth: 1,
    borderColor: "#f5e4c9",
    borderRadius: 10,
    padding: 10,
  },
  icon: {
    marginTop: 2,
  },
  content: {
    flex: 1,
    gap: 3,
  },
  label: {
    fontSize: 9,
    fontFamily: fontFamily.extrabold,
    color: "#8b5a1e",
    letterSpacing: 0,
  },
  explanation: {
    fontSize: 11,
    fontFamily: fontFamily.semibold,
    color: "#6b4515",
    lineHeight: 16,
  },
});
