import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { BrandMark } from "@/components/shell/BrandMark";
import { Icons } from "@/components/ui/Icon";
import { useRecalls } from "@/hooks/useRecalls";
import { useSearch } from "@/hooks/useSearch";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import type { RecentMemory, SearchResult } from "@/types/api";
import { formatDate, memoryTypeLabel, truncate } from "@/utils/format";

type MemoryRowItem = RecentMemory | SearchResult;

const PROMPTS = [
  "What do I know about distribution?",
  "What have I learned but not applied?",
];

function isRecentMemory(item: MemoryRowItem): item is RecentMemory {
  return "created_at" in item;
}

export default function SearchScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data: recallData } = useRecalls();
  const hasUnreadRecalls = (recallData?.memories?.length ?? 0) > 0;

  const {
    query,
    setQuery,
    searchResult,
    searching,
    recent,
    recentHasMore,
    loadingRecent,
    error,
    deletingId,
    executeSearch,
    clearSearch,
    loadMoreRecent,
    handleDelete,
  } = useSearch();

  const visibleMemories = searchResult ? searchResult.results : recent;
  const showingResults = Boolean(searchResult);

  const deleteWithConfirm = (memory: MemoryRowItem) => {
    Alert.alert(
      "Delete memory?",
      "This permanently removes it from Crowscap.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => handleDelete(memory.memory_id),
        },
      ]
    );
  };

  const openMemory = (memoryId: string) => {
    router.push({ pathname: "/(modals)/memory/[id]", params: { id: memoryId } } as never);
  };

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerBrand}>
          <BrandMark size={38} imageSize={29} />
          <View>
            <Text style={styles.headerTitle}>Search</Text>
            <Text style={styles.headerSub}>Explore memory</Text>
          </View>
        </View>
        <View style={styles.headerActions}>
          <Pressable onPress={() => router.push("/(tabs)/recall" as never)} hitSlop={8} style={styles.iconButton}>
            <Icons.Bell size={19} color={tokens.colors.text} />
            {hasUnreadRecalls ? <View style={styles.bellDot} /> : null}
          </Pressable>
          <Pressable onPress={() => router.push("/settings" as never)} hitSlop={8} style={styles.iconButton}>
            <Icons.Settings size={19} color={tokens.colors.text} />
          </Pressable>
        </View>
      </View>

      <ScrollView
        style={styles.content}
        contentContainerStyle={[styles.contentInner, { paddingBottom: insets.bottom + 96 }]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.searchHero}>
          <Text style={styles.eyebrow}>YOUR MEMORY</Text>
          <Text style={styles.heroTitle}>What are you trying to reach?</Text>

          <View style={styles.searchBox}>
            <Icons.Search size={18} color="#8a8e94" />
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder={'Try "what did I learn about customers?"'}
              placeholderTextColor="#8a8e94"
              style={styles.searchInput}
              returnKeyType="search"
              onSubmitEditing={() => executeSearch(query)}
              autoCapitalize="none"
              autoCorrect
            />
            {query ? (
              <Pressable onPress={clearSearch} hitSlop={8} style={styles.clearButton}>
                <Icons.X size={16} color="#757a80" />
              </Pressable>
            ) : null}
            <Pressable
              onPress={() => executeSearch(query)}
              disabled={searching || query.trim().length < 2}
              style={[
                styles.searchSubmit,
                (searching || query.trim().length < 2) && styles.searchSubmitDisabled,
              ]}
            >
              {searching ? (
                <ActivityIndicator size="small" color="#ffffff" />
              ) : (
                <Icons.ArrowRight size={18} color="#ffffff" />
              )}
            </Pressable>
          </View>

          <View style={styles.promptList}>
            {PROMPTS.map((prompt) => (
              <Pressable
                key={prompt}
                style={({ pressed }) => [styles.promptRow, pressed && styles.promptRowPressed]}
                onPress={() => {
                  setQuery(prompt);
                  executeSearch(prompt);
                }}
              >
                <Text style={styles.promptText}>{prompt}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {error ? (
          <View style={styles.errorBox}>
            <Icons.CircleAlert size={16} color="#9b4c51" />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <View style={styles.sectionHead}>
          <Text style={styles.eyebrow}>{showingResults ? "SEARCH RESULTS" : "RECENTLY SAVED"}</Text>
          <Text style={styles.sectionTitle}>
            {showingResults ? "Matches from your memory" : "Your newest memories"}
          </Text>
        </View>

        {loadingRecent && !showingResults ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator size="small" color={tokens.colors.text} />
            <Text style={styles.loadingText}>Loading recent memories.</Text>
          </View>
        ) : visibleMemories.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyTitle}>
              {showingResults ? "No matching memories yet." : "No memories saved yet."}
            </Text>
            <Text style={styles.emptyBody}>
              {showingResults
                ? "Try a simpler phrase or search for the topic in your own words."
                : "Save a useful note, link, video, or PDF and it will appear here."}
            </Text>
          </View>
        ) : (
          <View style={styles.memoryList}>
            {visibleMemories.map((memory) => (
              <MemoryRow
                key={memory.memory_id}
                item={memory}
                deleting={deletingId === memory.memory_id}
                onOpen={() => openMemory(memory.memory_id)}
                onDelete={() => deleteWithConfirm(memory)}
              />
            ))}

          </View>
        )}

        {!showingResults && recentHasMore ? (
          <Pressable style={styles.loadMoreButton} onPress={loadMoreRecent} disabled={loadingRecent}>
            {loadingRecent ? (
              <ActivityIndicator size="small" color={tokens.colors.text} />
            ) : (
              <Text style={styles.loadMoreText}>Load more</Text>
            )}
          </Pressable>
        ) : null}
      </ScrollView>
    </View>
  );
}

function cleanSourceTitle(raw: string | null | undefined): string {
  if (!raw) return "Saved source";
  try {
    return decodeURIComponent(raw).replace(/%20/g, " ");
  } catch {
    return raw.replace(/%20/g, " ");
  }
}

function MemoryRow({
  item,
  deleting,
  onOpen,
  onDelete,
}: {
  item: MemoryRowItem;
  deleting: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const sourceType = isRecentMemory(item) ? item.source_type : null;
  const date = isRecentMemory(item) ? formatDate(item.created_at) : null;
  const sourceTitle = cleanSourceTitle(item.source_title);

  return (
    <View style={styles.memoryRow}>
      <Pressable
        onPress={onOpen}
        style={({ pressed }) => [styles.memoryOpenArea, pressed && styles.memoryOpenAreaPressed]}
      >
        <View style={styles.memoryIcon}>
          {sourceType === "pdf" ? (
            <Icons.FileText size={15} color="#2d7058" />
          ) : (
            <Icons.BookOpenCheck size={15} color="#2d7058" />
          )}
        </View>
        <View style={styles.memoryBody}>
          <View style={styles.metaRow}>
            <Text style={styles.metaText}>{memoryTypeLabel(item.memory_type).toUpperCase()}</Text>
            {sourceType ? <Text style={styles.metaDot}>·</Text> : null}
            {sourceType ? <Text style={styles.metaText}>{sourceType.toUpperCase()}</Text> : null}
            {date ? (
              <View style={styles.dateMeta}>
                <Icons.Clock3 size={11} color="#8c9096" />
                <Text style={styles.dateText}>{date}</Text>
              </View>
            ) : null}
          </View>
          <Text style={styles.memoryTitle} numberOfLines={2}>
            {isRecentMemory(item) ? item.summary || item.content : item.content}
          </Text>
          <Text style={styles.memorySource} numberOfLines={1}>
            {sourceTitle}
          </Text>
        </View>
      </Pressable>
      <Pressable onPress={onDelete} hitSlop={8} style={styles.deleteButton} disabled={deleting}>
        {deleting ? (
          <ActivityIndicator size="small" color="#9b4c51" />
        ) : (
          <Icons.Trash2 size={16} color="#9b4c51" />
        )}
      </Pressable>
    </View>
  );
}



const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing[4],
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f1f3",
    backgroundColor: "#ffffff",
  },
  headerBrand: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  headerTitle: {
    fontSize: 19,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  headerSub: {
    marginTop: 2,
    fontSize: 13,
    color: tokens.colors.textMuted,
    fontFamily: fontFamily.medium,
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  bellDot: {
    position: "absolute",
    top: 7,
    right: 7,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#2d7058",
  },
  iconButton: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
  },
  content: {
    flex: 1,
  },
  contentInner: {
    backgroundColor: "#ffffff",
  },  searchHero: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f1f3",
  },
  eyebrow: {
    fontSize: 10.5,
    fontFamily: fontFamily.extrabold,
    color: "#787c80",
    marginBottom: 4,
    letterSpacing: 0.5,
  },
  heroTitle: {
    fontSize: 21,
    lineHeight: 27,
    fontFamily: fontFamily.bold,
    color: "#111418",
    marginBottom: 16,
  },
  searchBox: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: "#e3e5e8",
    borderRadius: 24,
    flexDirection: "row",
    alignItems: "center",
    paddingLeft: 14,
    paddingRight: 5,
    gap: 8,
    backgroundColor: "#ffffff",
  },
  searchInput: {
    flex: 1,
    minHeight: 44,
    fontSize: 13.5,
    color: "#111418",
    fontFamily: fontFamily.medium,
  },
  clearButton: {
    width: 26,
    height: 26,
    alignItems: "center",
    justifyContent: "center",
  },
  searchSubmit: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#111111",
  },
  searchSubmitDisabled: {
    backgroundColor: "#c7c9cc",
  },
  promptList: {
    marginTop: 14,
    gap: 8,
  },
  promptRow: {
    minHeight: 42,
    borderWidth: 1,
    borderColor: "#e8eaec",
    borderRadius: 8,
    justifyContent: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: "#f7f8f9",
  },
  promptRowPressed: {
    backgroundColor: "#eceeed",
  },
  promptText: {
    fontSize: 13,
    lineHeight: 18,
    color: "#303438",
    fontFamily: fontFamily.semibold,
  },
  errorBox: {
    marginHorizontal: 20,
    marginTop: 14,
    borderWidth: 1,
    borderColor: "#f1cccc",
    borderRadius: 10,
    backgroundColor: "#fff6f6",
    padding: 12,
    flexDirection: "row",
    gap: 8,
  },
  errorText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 18,
    color: "#9b4c51",
    fontFamily: fontFamily.semibold,
  },
  sectionHead: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f1f3",
  },
  sectionTitle: {
    fontSize: 18,
    lineHeight: 24,
    fontFamily: fontFamily.bold,
    color: "#111418",
  },
  loadingRow: {
    paddingVertical: 24,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  loadingText: {
    fontSize: 13,
    color: tokens.colors.textMuted,
    fontFamily: fontFamily.semibold,
  },
  emptyState: {
    paddingHorizontal: 20,
    paddingTop: 28,
    gap: 8,
  },
  emptyTitle: {
    fontSize: 17,
    fontFamily: fontFamily.bold,
    color: "#111418",
  },
  emptyBody: {
    fontSize: 13,
    lineHeight: 19,
    color: tokens.colors.textMuted,
    fontFamily: fontFamily.medium,
  },
  memoryList: {
    backgroundColor: "#ffffff",
  },
  memoryRow: {
    flexDirection: "row",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: "#f0f1f3",
    paddingLeft: 20,
    paddingRight: 12,
    backgroundColor: "#ffffff",
  },
  memoryOpenArea: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 13,
  },
  memoryOpenAreaPressed: {
    opacity: 0.72,
  },
  memoryIcon: {
    width: 34,
    height: 34,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#e8f4ed",
  },
  memoryBody: {
    flex: 1,
    gap: 3,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  metaText: {
    fontSize: 10,
    color: "#787c80",
    fontFamily: fontFamily.extrabold,
    letterSpacing: 0.5,
  },
  metaDot: {
    fontSize: 11,
    color: "#b0b4b8",
  },
  dateMeta: {
    marginLeft: "auto",
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  dateText: {
    fontSize: 11,
    color: "#8a8e94",
    fontFamily: fontFamily.medium,
  },
  memoryTitle: {
    fontSize: 13.5,
    lineHeight: 19,
    color: "#111418",
    fontFamily: fontFamily.bold,
  },
  memorySource: {
    fontSize: 11.5,
    lineHeight: 16,
    color: "#8a8e94",
    fontFamily: fontFamily.medium,
  },
  deleteButton: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
  },
  loadMoreButton: {
    alignSelf: "center",
    marginTop: 18,
    minWidth: 120,
    minHeight: 40,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#e1e3e7",
    borderRadius: 8,
    backgroundColor: "#ffffff",
  },
  loadMoreText: {
    fontSize: 13,
    color: "#111418",
    fontFamily: fontFamily.bold,
  },
});
