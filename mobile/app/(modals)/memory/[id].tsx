import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  Linking,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useEffect, useRef, useState } from "react";
import { apiRequest } from "@/api/client";
import { archiveMemory } from "@/api/memories";
import { MemoryTypeBadge } from "@/components/memory/MemoryTypeBadge";
import { ConfidencePill } from "@/components/memory/ConfidencePill";
import { tokens } from "@/theme/tokens";
import { Icons } from "@/components/ui/Icon";
import { fontFamily } from "@/theme/typography";

// ---- Types ----

interface MemoryRelationDetail {
  related_memory_id: string;
  relationship_type: string;
  strength: string;
  explanation: string;
}

interface MemoryAtomDetail {
  id: string;
  memory_type: string;
  epistemic_label: string | null;
  content: string;
  summary: string | null;
  confidence: string;
  confidence_reason: string | null;
  source_strength: string;
  relationships: MemoryRelationDetail[];
}

interface SourceMemoriesResponse {
  source_id: string;
  source_title: string | null;
  source_type: string;
  source_url: string | null;
  memories: MemoryAtomDetail[];
}

// ---- Helpers ----

const URL_REGEX = /https?:\/\/[^\s]+/g;

function containsUrl(text: string): boolean {
  return URL_REGEX.test(text);
}

function extractFirstUrl(text: string): string | null {
  const match = text.match(URL_REGEX);
  return match ? match[0] : null;
}

function isLinkAtom(atom: MemoryAtomDetail): boolean {
  return (
    atom.memory_type === "reference" ||
    containsUrl(atom.content) ||
    containsUrl(atom.summary ?? "")
  );
}

function getSourceTypeLabel(sourceType: string): string {
  const labels: Record<string, string> = {
    url: "Web Link",
    pdf: "PDF",
    chat: "Chat",
    text: "Text",
    file: "File",
  };
  return labels[sourceType?.toLowerCase()] ?? sourceType ?? "Source";
}

// ---- Main Component ----

export default function MemoryDetailModal() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id, source_id } = useLocalSearchParams<{ id: string; source_id?: string }>();

  const [data, setData] = useState<SourceMemoriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [archiving, setArchiving] = useState<string | null>(null); // memory id being archived

  const scrollRef = useRef<ScrollView>(null);
  const atomLayouts = useRef<Record<string, number>>({});

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    const fetchData = async () => {
      try {
        if (source_id) {
          // Preferred: fetch all atoms from the same source
          const result = await apiRequest<SourceMemoriesResponse>(`/memories/by-source/${source_id}`);
          if (!cancelled) setData(result);
        } else {
          // Fallback: fetch just the single atom and wrap it
          const mem = await apiRequest<MemoryAtomDetail>(`/memories/${id}`);
          if (!cancelled) {
            setData({
              source_id: "",
              source_title: null,
              source_type: "chat",
              source_url: null,
              memories: [mem],
            });
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load memory.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void fetchData();
    return () => { cancelled = true; };
  }, [id, source_id]);

  // Auto-scroll to the highlighted atom after layout
  const scrollToHighlighted = () => {
    if (!id) return;
    const y = atomLayouts.current[id];
    if (y !== undefined && scrollRef.current) {
      scrollRef.current.scrollTo({ y: Math.max(0, y - 24), animated: true });
    }
  };

  const handleArchive = (memId: string) => {
    if (archiving) return;
    Alert.alert(
      "Archive Memory",
      "Are you sure you want to archive this memory? It will no longer surface in search or recall.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Archive",
          style: "destructive",
          onPress: async () => {
            setArchiving(memId);
            try {
              await archiveMemory(memId);
              // Remove from local list
              setData((prev) =>
                prev
                  ? { ...prev, memories: prev.memories.filter((m) => m.id !== memId) }
                  : prev
              );
            } catch (err) {
              setArchiving(null);
              Alert.alert(
                "Error",
                err instanceof Error ? err.message : "Could not archive memory."
              );
            } finally {
              setArchiving(null);
            }
          },
        },
      ]
    );
  };

  const highlighted = data?.memories.find((m) => m.id === id);
  const sourceUrl = data?.source_url ?? extractFirstUrl(highlighted?.content ?? "");

  return (
    <View style={styles.root}>
      <View style={styles.handleBar} />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          {data && (
            <View style={styles.sourceTypeBadge}>
              <Text style={styles.sourceTypeBadgeText}>
                {getSourceTypeLabel(data.source_type)}
              </Text>
            </View>
          )}
          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle} numberOfLines={1}>
              {data?.source_title
                ? data.source_title.length > 40
                  ? data.source_title.slice(0, 40) + "…"
                  : data.source_title
                : "Memory Detail"}
            </Text>
            <Text style={styles.headerSub}>
              {data ? `${data.memories.length} ${data.memories.length === 1 ? "atom" : "atoms"} from this source` : "Source-aware atomic memory"}
            </Text>
          </View>
        </View>
        <Pressable style={styles.closeBtn} onPress={() => router.back()} hitSlop={8}>
          <Icons.X size={18} color="#777a7e" />
        </Pressable>
      </View>

      {/* Source URL chip */}
      {sourceUrl ? (
        <Pressable
          style={styles.sourceUrlChip}
          onPress={() => Linking.openURL(sourceUrl)}
        >
          <Icons.Link size={12} color="#1a6ebd" />
          <Text style={styles.sourceUrlText} numberOfLines={1}>
            {sourceUrl}
          </Text>
          <Icons.ExternalLink size={12} color="#1a6ebd" />
        </Pressable>
      ) : null}

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="small" color={tokens.colors.text} />
          <Text style={styles.loadingText}>Loading memories…</Text>
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Icons.AlertCircle size={24} color={tokens.colors.danger} />
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={() => router.back()} style={styles.backBtn}>
            <Text style={styles.backBtnText}>Go back</Text>
          </Pressable>
        </View>
      ) : !data || data.memories.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>No memories found.</Text>
        </View>
      ) : (
        <ScrollView
          ref={scrollRef}
          style={styles.scroll}
          contentContainerStyle={[
            styles.scrollContent,
            { paddingBottom: insets.bottom + 40 },
          ]}
          showsVerticalScrollIndicator={false}
          onLayout={scrollToHighlighted}
        >
          {data.memories.map((mem) => {
            const isHighlighted = mem.id === id;
            const isLink = isLinkAtom(mem);
            const memUrl = extractFirstUrl(mem.content) ?? extractFirstUrl(mem.summary ?? "");

            return (
              <View
                key={mem.id}
                style={[
                  styles.atomCard,
                  isHighlighted && styles.atomCardHighlighted,
                ]}
                onLayout={(e) => {
                  atomLayouts.current[mem.id] = e.nativeEvent.layout.y;
                  if (isHighlighted) scrollToHighlighted();
                }}
              >
                {/* Highlight bar */}
                {isHighlighted && <View style={styles.highlightBar} />}

                {/* Atom header */}
                <View style={styles.atomHeader}>
                  <MemoryTypeBadge type={mem.memory_type as any} />
                  {mem.epistemic_label ? (
                    <View style={styles.epistemicBadge}>
                      <Text style={styles.epistemicText}>
                        {mem.epistemic_label.replace(/_/g, " ")}
                      </Text>
                    </View>
                  ) : null}
                  <ConfidencePill confidence={mem.confidence as any} />
                  {isHighlighted && (
                    <View style={styles.focusedBadge}>
                      <Text style={styles.focusedBadgeText}>FOCUSED</Text>
                    </View>
                  )}
                </View>

                {/* Content */}
                <View style={styles.contentBox}>
                  <Text style={styles.contentText}>{mem.content}</Text>
                </View>

                {/* URL chip for link atoms */}
                {isLink && memUrl ? (
                  <Pressable
                    style={styles.linkChip}
                    onPress={() => Linking.openURL(memUrl)}
                  >
                    <Icons.Link size={12} color="#1a6ebd" />
                    <Text style={styles.linkChipText} numberOfLines={1}>
                      {memUrl}
                    </Text>
                    <Icons.ExternalLink size={11} color="#1a6ebd" />
                  </Pressable>
                ) : null}

                {/* Summary */}
                {mem.summary ? (
                  <View style={styles.summaryBox}>
                    <Text style={styles.summaryLabel}>SUMMARY</Text>
                    <Text style={styles.summaryText}>{mem.summary}</Text>
                  </View>
                ) : null}

                {/* Confidence reason */}
                {mem.confidence_reason ? (
                  <View style={styles.reasonBox}>
                    <Icons.Info size={11} color="#7b7e82" style={{ marginTop: 1 }} />
                    <Text style={styles.reasonText}>{mem.confidence_reason}</Text>
                  </View>
                ) : null}

                {/* Archive only on focused atom */}
                {isHighlighted && (
                  <Pressable
                    style={({ pressed }) => [
                      styles.archiveBtn,
                      pressed && { opacity: 0.8 },
                    ]}
                    onPress={() => handleArchive(mem.id)}
                    disabled={archiving === mem.id}
                  >
                    {archiving === mem.id ? (
                      <ActivityIndicator size="small" color="#9b4c51" />
                    ) : (
                      <>
                        <Icons.Archive size={14} color="#9b4c51" />
                        <Text style={styles.archiveBtnText}>Archive this memory</Text>
                      </>
                    )}
                  </Pressable>
                )}
              </View>
            );
          })}
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
    gap: 12,
  },
  headerLeft: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  sourceTypeBadge: {
    backgroundColor: "#e8f1f5",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  sourceTypeBadgeText: {
    fontSize: 10,
    fontFamily: fontFamily.extrabold,
    color: "#356b8f",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  headerTitle: {
    fontSize: 15,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
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

  sourceUrlChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginHorizontal: tokens.spacing[5],
    marginTop: 10,
    marginBottom: 2,
    backgroundColor: "#eef4fb",
    borderWidth: 1,
    borderColor: "#c5daf5",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  sourceUrlText: {
    flex: 1,
    fontSize: 12,
    fontFamily: fontFamily.medium,
    color: "#1a6ebd",
  },

  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[6],
  },
  loadingText: {
    fontSize: 12,
    fontFamily: fontFamily.medium,
    color: tokens.colors.textMuted,
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
    paddingHorizontal: tokens.spacing[4],
    paddingTop: 20,
    gap: 12,
  },

  atomCard: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 14,
    padding: tokens.spacing[4],
    backgroundColor: "#fafafa",
    gap: 10,
    overflow: "hidden",
  },
  atomCardHighlighted: {
    borderColor: "#a8d4be",
    backgroundColor: "#f4fbf7",
  },
  highlightBar: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    width: 4,
    backgroundColor: "#2d7058",
    borderTopLeftRadius: 14,
    borderBottomLeftRadius: 14,
  },

  atomHeader: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 6,
    paddingLeft: 6, // account for highlight bar
  },
  epistemicBadge: {
    backgroundColor: "#f2f3f4",
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 3,
  },
  epistemicText: {
    fontSize: 10,
    fontFamily: fontFamily.bold,
    color: "#555860",
    textTransform: "capitalize",
  },
  focusedBadge: {
    backgroundColor: "#d8efe5",
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 3,
  },
  focusedBadgeText: {
    fontSize: 9,
    fontFamily: fontFamily.extrabold,
    color: "#2d7058",
    letterSpacing: 0.5,
  },

  contentBox: {
    paddingLeft: 6,
  },
  contentText: {
    fontSize: 14,
    fontFamily: fontFamily.medium,
    color: "#1d1e1f",
    lineHeight: 22,
  },

  linkChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#eef4fb",
    borderWidth: 1,
    borderColor: "#c5daf5",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
    marginLeft: 6,
  },
  linkChipText: {
    flex: 1,
    fontSize: 12,
    fontFamily: fontFamily.medium,
    color: "#1a6ebd",
  },

  summaryBox: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 10,
    padding: tokens.spacing[3],
    backgroundColor: "#ffffff",
    gap: 4,
    marginLeft: 6,
  },
  summaryLabel: {
    fontSize: 9,
    fontFamily: fontFamily.extrabold,
    color: "#8a8d90",
    letterSpacing: 0.5,
    textTransform: "uppercase",
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
    marginLeft: 6,
  },
  reasonText: {
    flex: 1,
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: "#676a6d",
    lineHeight: 16,
  },

  archiveBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    height: 42,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#f5d0d0",
    backgroundColor: "#fff5f5",
    marginTop: 4,
    marginLeft: 6,
  },
  archiveBtnText: {
    fontSize: 12,
    fontFamily: fontFamily.extrabold,
    color: "#9b4c51",
  },
});
