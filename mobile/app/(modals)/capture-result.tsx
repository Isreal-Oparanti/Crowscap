import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Icons } from "@/components/ui/Icon";
import type { CaptureResponse } from "@/types/api";
import { memoryTypeLabel } from "@/utils/format";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";

export default function CaptureResultModal() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ data: string }>();

  let data: CaptureResponse | null = null;
  try {
    if (params.data) data = JSON.parse(params.data) as CaptureResponse;
  } catch {
    // bad data — show fallback
  }

  if (!data) {
    return (
      <View style={styles.root}>
        <View style={styles.handleBar} />
        <View style={styles.errorWrap}>
          <Text style={styles.errorText}>Could not display capture result.</Text>
          <Pressable onPress={() => router.back()} style={styles.doneButton}>
            <Text style={styles.doneButtonText}>Close</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  const memCount = data.memories.length;

  return (
    <View style={styles.root}>
      <View style={styles.handleBar} />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.checkCircle}>
            <Icons.Check size={16} color="#245e4b" />
          </View>
          <View>
            <Text style={styles.headerTitle}>Memory saved</Text>
            <Text style={styles.headerSub}>
              {memCount} {memCount === 1 ? "memory" : "memories"} extracted
            </Text>
          </View>
        </View>
        <Pressable
          style={styles.doneButtonSmall}
          onPress={() => router.dismiss()}
          hitSlop={8}
        >
          <Text style={styles.doneButtonSmallText}>Done</Text>
        </Pressable>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: insets.bottom + 32 },
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* Source */}
        {data.source_title ? (
          <View style={styles.sourceRow}>
            <Icons.FileText size={12} color="#8a8d90" />
            <Text style={styles.sourceTitle} numberOfLines={2}>
              {data.source_title}
            </Text>
          </View>
        ) : null}

        {/* Intents */}
        {data.inferred_intents.length > 0 ? (
          <View style={styles.intentRow}>
            {data.inferred_intents.map((intent) => (
              <View key={intent} style={styles.intentBadge}>
                <Text style={styles.intentBadgeText}>{intent}</Text>
              </View>
            ))}
          </View>
        ) : null}

        {/* Memory atoms */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>EXTRACTED MEMORIES</Text>
          <View style={styles.memoriesList}>
            {data.memories.map((mem) => (
              <View key={mem.id} style={styles.memoryCard}>
                {/* Type + confidence row */}
                <View style={styles.memoryMeta}>
                  <View style={styles.typeBadge}>
                    <Text style={styles.typeBadgeText}>
                      {memoryTypeLabel(mem.memory_type)}
                    </Text>
                  </View>
                  <View style={[styles.confidenceDot, styles[`confidence_${mem.confidence}`]]} />
                  <Text style={styles.confidenceText}>{mem.confidence}</Text>
                </View>

                {/* Content */}
                <Text style={styles.memoryContent}>{mem.content}</Text>

                {/* Summary */}
                {mem.summary ? (
                  <Text style={styles.memorySummary}>{mem.summary}</Text>
                ) : null}

                {/* Relations */}
                {mem.relationships?.length > 0 ? (
                  <View style={styles.tensionRow}>
                    <Icons.GitMerge size={10} color="#7c8083" />
                    <Text style={styles.tensionText}>
                      {mem.relationships.length} relation{mem.relationships.length > 1 ? "s" : ""} detected
                    </Text>
                  </View>
                ) : null}
              </View>
            ))}
          </View>
        </View>

        {/* CTA */}
        <Pressable
          style={({ pressed }) => [
            styles.doneButton,
            pressed && { opacity: 0.85 },
          ]}
          onPress={() => router.dismiss()}
        >
          <Text style={styles.doneButtonText}>Back to chat</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  handleBar: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: "#d1d3d5",
    alignSelf: "center",
    marginTop: 10,
    marginBottom: 4,
  },
  errorWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing[4],
    paddingHorizontal: tokens.spacing[6],
  },
  errorText: {
    fontSize: 14,
    fontFamily: fontFamily.medium,
    color: tokens.colors.textMuted,
    textAlign: "center",
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing[5],
    paddingVertical: tokens.spacing[4],
    borderBottomWidth: 1,
    borderBottomColor: "#e7e8e9",
  },
  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[3],
  },
  checkCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#edf5f1",
    alignItems: "center",
    justifyContent: "center",
  },
  headerTitle: {
    fontSize: 15,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
    letterSpacing: 0,
  },
  headerSub: {
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: tokens.colors.textMuted,
    marginTop: 1,
  },
  doneButtonSmall: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  doneButtonSmallText: {
    fontSize: 12,
    fontFamily: fontFamily.bold,
    color: tokens.colors.text,
  },

  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: tokens.spacing[5],
    paddingTop: tokens.spacing[5],
    gap: tokens.spacing[5],
  },

  sourceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#f5f6f7",
    borderRadius: 8,
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[2],
  },
  sourceTitle: {
    fontSize: 12,
    fontFamily: fontFamily.semibold,
    color: "#555860",
    flex: 1,
  },

  intentRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  intentBadge: {
    borderWidth: 1,
    borderColor: "#dfe1e3",
    borderRadius: tokens.radius.full,
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: "#f7f8f9",
  },
  intentBadgeText: {
    fontSize: 10,
    fontFamily: fontFamily.bold,
    color: "#4d5154",
    letterSpacing: 0,
  },

  section: { gap: tokens.spacing[3] },
  sectionLabel: {
    fontSize: 10,
    fontFamily: fontFamily.extrabold,
    color: "#8a8d90",
    letterSpacing: 0,
  },

  memoriesList: { gap: tokens.spacing[3] },
  memoryCard: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 14,
    padding: tokens.spacing[4],
    backgroundColor: "#ffffff",
    gap: tokens.spacing[2],
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 4,
    elevation: 1,
  },
  memoryMeta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  typeBadge: {
    backgroundColor: "#f2f3f4",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  typeBadgeText: {
    fontSize: 10,
    fontFamily: fontFamily.extrabold,
    color: "#4d5154",
    letterSpacing: 0,
  },
  confidenceDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    marginLeft: 4,
  },
  confidence_high: { backgroundColor: "#2d7058" },
  confidence_medium: { backgroundColor: "#b07030" },
  confidence_low: { backgroundColor: "#9b4c51" },
  confidence_unknown: { backgroundColor: "#b4b7b9" },
  confidenceText: {
    fontSize: 10,
    fontFamily: fontFamily.semibold,
    color: "#8a8d90",
  },
  memoryContent: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#252627",
    lineHeight: 20,
  },
  memorySummary: {
    fontSize: 11,
    fontFamily: fontFamily.regular,
    color: "#787c80",
    lineHeight: 16,
  },
  tensionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 2,
  },
  tensionText: {
    fontSize: 10,
    fontFamily: fontFamily.semibold,
    color: "#7c8083",
  },

  doneButton: {
    height: 52,
    borderRadius: 12,
    backgroundColor: tokens.colors.text,
    alignItems: "center",
    justifyContent: "center",
  },
  doneButtonText: {
    fontSize: 14,
    fontFamily: fontFamily.extrabold,
    color: "#ffffff",
    letterSpacing: 0,
  },
});
