import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getSourceContent, type SourceContentResponse } from "@/api/sources";
import { Icons } from "@/components/ui/Icon";
import { MarkdownText } from "@/components/ui/MarkdownText";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";

export default function SourceModal() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();

  const [data, setData] = useState<SourceContentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSource = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const res = await getSourceContent(id);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load document content.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSource();
  }, [fetchSource]);

  const cleanTitle = (raw: string | null) => {
    if (!raw) return "Original Document";
    try {
      const decoded = decodeURIComponent(raw);
      return decoded.replace(/^#{1,6}\s+/, "").trim();
    } catch {
      return raw;
    }
  };

  return (
    <View style={[styles.root, { paddingTop: Math.max(insets.top, 16) }]}>
      <View style={styles.handleBar} />

      {/* Top Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>
              {(data?.source_type || "DOCUMENT").toUpperCase()}
            </Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle} numberOfLines={1}>
              {cleanTitle(data?.title ?? null)}
            </Text>
            <Text style={styles.headerSub}>Full Original Source Document</Text>
          </View>
        </View>
        <Pressable style={styles.closeBtn} onPress={() => router.back()} hitSlop={8}>
          <Icons.X size={18} color="#777a7e" />
        </Pressable>
      </View>

      {/* Original URL Chip */}
      {data?.original_url ? (
        <Pressable
          style={styles.linkChip}
          onPress={() => Linking.openURL(data.original_url!)}
        >
          <Icons.Link size={12} color="#111827" />
          <Text style={styles.linkText} numberOfLines={1}>
            {data.original_url}
          </Text>
          <Icons.ExternalLink size={12} color="#111827" />
        </Pressable>
      ) : null}

      {/* Content Body */}
      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="small" color={tokens.colors.text} />
          <Text style={styles.loadingText}>Loading document content…</Text>
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryBtn} onPress={fetchSource}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 40 }]}
          showsVerticalScrollIndicator={true}
        >
          <MarkdownText
            text={data?.original_content || "No original content stored for this capture."}
          />
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
    backgroundColor: "#d1d5db",
    alignSelf: "center",
    marginBottom: 10,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  headerLeft: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginRight: 10,
  },
  badge: {
    backgroundColor: "#f3f4f6",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  badgeText: {
    fontSize: 10,
    fontFamily: fontFamily.extrabold,
    color: "#374151",
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
  linkChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginHorizontal: 20,
    marginTop: 12,
    marginBottom: 4,
    backgroundColor: "#f9fafb",
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  linkText: {
    flex: 1,
    fontSize: 12,
    fontFamily: fontFamily.medium,
    color: "#111827",
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    gap: 12,
  },
  loadingText: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: tokens.colors.textMuted,
  },
  errorText: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#dc2626",
    textAlign: "center",
  },
  retryBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#f3f4f6",
  },
  retryText: {
    fontSize: 12,
    fontFamily: fontFamily.bold,
    color: tokens.colors.text,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
});
