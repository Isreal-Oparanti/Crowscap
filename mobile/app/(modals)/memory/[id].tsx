import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useEffect, useState } from "react";
import { apiRequest } from "@/api/client";
import { archiveMemory } from "@/api/memories";
import type { MemoryAtom } from "@/types/api";
import { MemoryTypeBadge } from "@/components/memory/MemoryTypeBadge";
import { ConfidencePill } from "@/components/memory/ConfidencePill";
import { RelationRow } from "@/components/memory/RelationRow";
import { tokens } from "@/theme/tokens";
import { Icons } from "@/components/ui/Icon";
import { fontFamily } from "@/theme/typography";

export default function MemoryDetailModal() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();

  const [memory, setMemory] = useState<MemoryAtom | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [archiving, setArchiving] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiRequest<MemoryAtom>(`/memories/${id}`)
      .then((data) => {
        if (!cancelled) setMemory(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load memory.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const handleArchive = () => {
    if (!id || archiving) return;
    Alert.alert(
      "Archive Memory",
      "Are you sure you want to archive this memory? It will no longer surface in search or recall.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Archive",
          style: "destructive",
          onPress: async () => {
            setArchiving(true);
            try {
              await archiveMemory(id);
              router.back();
            } catch (err) {
              setArchiving(false);
              Alert.alert(
                "Error",
                err instanceof Error ? err.message : "Could not archive memory."
              );
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.root}>
      <View style={styles.handleBar} />

      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Memory Detail</Text>
          <Text style={styles.headerSub}>Source-aware atomic memory</Text>
        </View>
        <Pressable style={styles.closeBtn} onPress={() => router.back()} hitSlop={8}>
          <Icons.X size={18} color="#777a7e" />
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="small" color={tokens.colors.text} />
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={() => router.back()} style={styles.backBtn}>
            <Text style={styles.backBtnText}>Go back</Text>
          </Pressable>
        </View>
      ) : !memory ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>Memory not found.</Text>
        </View>
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={[
            styles.scrollContent,
            { paddingBottom: insets.bottom + 32 },
          ]}
          showsVerticalScrollIndicator={false}
        >
          {/* Metadata badges */}
          <View style={styles.badgeRow}>
            <MemoryTypeBadge type={memory.memory_type} />
            {memory.epistemic_label ? (
              <View style={styles.epistemicBadge}>
                <Text style={styles.epistemicText}>
                  {memory.epistemic_label.replace("_", " ")}
                </Text>
              </View>
            ) : null}
            <ConfidencePill confidence={memory.confidence} />
          </View>

          {/* Main Content */}
          <View style={styles.contentBox}>
            <Text style={styles.contentText}>{memory.content}</Text>
          </View>

          {/* Summary Box */}
          {memory.summary ? (
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>SUMMARY</Text>
              <View style={styles.summaryBox}>
                <Text style={styles.summaryText}>{memory.summary}</Text>
              </View>
            </View>
          ) : null}

          {/* Confidence Reason Box */}
          {memory.confidence_reason ? (
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>EVIDENCE CONFIDENCE REASON</Text>
              <View style={styles.reasonBox}>
                <Icons.Info size={12} color="#7b7e82" style={{ marginTop: 2 }} />
                <Text style={styles.reasonText}>{memory.confidence_reason}</Text>
              </View>
            </View>
          ) : null}

          {/* Relationships */}
          {memory.relationships && memory.relationships.length > 0 ? (
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                CONNECTED MEMORIES ({memory.relationships.length})
              </Text>
              <View style={styles.relationList}>
                {memory.relationships.map((rel, idx) => (
                  <RelationRow key={idx} relation={rel} />
                ))}
              </View>
            </View>
          ) : null}

          {/* Archive CTA */}
          <Pressable
            style={({ pressed }) => [
              styles.archiveBtn,
              pressed && { opacity: 0.8 },
            ]}
            onPress={handleArchive}
            disabled={archiving}
          >
            {archiving ? (
              <ActivityIndicator size="small" color="#9b4c51" />
            ) : (
              <>
                <Icons.Archive size={15} color="#9b4c51" />
                <Text style={styles.archiveBtnText}>Archive memory</Text>
              </>
            )}
          </Pressable>
        </ScrollView>
      )}
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
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing[5],
    paddingVertical: tokens.spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: "#e7e8e9",
  },
  headerTitle: {
    fontSize: 16,
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
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#f1f2f3",
    alignItems: "center",
    justifyContent: "center",
  },

  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[6],
  },
  errorText: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: tokens.colors.danger,
    textAlign: "center",
  },
  backBtn: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  backBtnText: {
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

  badgeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  epistemicBadge: {
    backgroundColor: "#f2f3f4",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  epistemicText: {
    fontSize: 10,
    fontFamily: fontFamily.bold,
    color: "#555860",
    textTransform: "capitalize",
  },

  contentBox: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 14,
    padding: tokens.spacing[4],
    backgroundColor: "#fafafa",
  },
  contentText: {
    fontSize: 14,
    fontFamily: fontFamily.medium,
    color: "#1d1e1f",
    lineHeight: 22,
  },

  section: {
    gap: tokens.spacing[2],
  },
  sectionLabel: {
    fontSize: 10,
    fontFamily: fontFamily.extrabold,
    color: "#8a8d90",
    letterSpacing: 0,
  },

  summaryBox: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 12,
    padding: tokens.spacing[3],
    backgroundColor: "#ffffff",
  },
  summaryText: {
    fontSize: 12,
    fontFamily: fontFamily.medium,
    color: "#464a4d",
    lineHeight: 18,
  },

  reasonBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    borderWidth: 1,
    borderColor: "#e8eaec",
    borderRadius: 10,
    padding: tokens.spacing[3],
    backgroundColor: "#fafafa",
  },
  reasonText: {
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: "#676a6d",
    lineHeight: 16,
    flex: 1,
  },

  relationList: {
    gap: 8,
  },

  archiveBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#f5d0d0",
    backgroundColor: "#fff5f5",
    marginTop: 12,
  },
  archiveBtnText: {
    fontSize: 13,
    fontFamily: fontFamily.extrabold,
    color: "#9b4c51",
  },
});
