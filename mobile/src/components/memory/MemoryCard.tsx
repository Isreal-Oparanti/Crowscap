import { View, Text, StyleSheet, Pressable } from "react-native";
import { useRouter } from "expo-router";
import type { MemoryAtom, RecentMemory, SearchResult } from "@/types/api";
import { MemoryTypeBadge } from "./MemoryTypeBadge";
import { ConfidencePill } from "./ConfidencePill";
import { SourceLink } from "./SourceLink";
import { RelationRow } from "./RelationRow";
import { fontFamily } from "@/theme/typography";

type DisplayMemory = MemoryAtom | RecentMemory | SearchResult;

export function MemoryCard({
  memory,
  onPress,
}: {
  memory: DisplayMemory;
  onPress?: () => void;
}) {
  const router = useRouter();
  const id = "id" in memory ? memory.id : memory.memory_id;
  const sourceTitle = "source_title" in memory ? memory.source_title : null;
  const sourceType = "source_type" in memory ? memory.source_type : "text";
  const relationships = "relationships" in memory ? memory.relationships : undefined;
  const score = "similarity_score" in memory ? memory.similarity_score : null;

  const handlePress = () => {
    if (onPress) {
      onPress();
    } else if (id) {
      router.push(`/(modals)/memory/${id}`);
    }
  };

  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      onPress={handlePress}
    >
      <View style={styles.topRow}>
        <MemoryTypeBadge type={memory.memory_type} />
        <ConfidencePill confidence={memory.confidence} />
        {score !== null ? (
          <Text style={styles.scoreText}>
            {Math.round(score * 100)}% match
          </Text>
        ) : null}
      </View>

      <Text style={styles.content}>{memory.content}</Text>

      {sourceTitle ? <SourceLink title={sourceTitle} type={sourceType} /> : null}

      {relationships && relationships.length > 0 ? (
        <View style={styles.relationSection}>
          <RelationRow relation={relationships[0]} />
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 14,
    padding: 14,
    backgroundColor: "#ffffff",
    gap: 10,
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 4,
    elevation: 1,
  },
  cardPressed: {
    backgroundColor: "#fcfcfc",
    borderColor: "#d2d5d7",
  },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  scoreText: {
    fontSize: 10,
    fontFamily: fontFamily.extrabold,
    color: "#2d7058",
    marginLeft: "auto",
  },
  content: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#252627",
    lineHeight: 20,
  },
  relationSection: {
    marginTop: 2,
  },
});
