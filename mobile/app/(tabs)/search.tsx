import {
  View,
  Text,
  StyleSheet,
  TextInput,
  ScrollView,
  Pressable,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useSearch } from "@/hooks/useSearch";
import { memoryTypeLabel, formatDate } from "@/utils/format";
import { tokens } from "@/theme/tokens";

export default function SearchScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const {
    query,
    setQuery,
    searchResult,
    searching,
    recent,
    recentHasMore,
    loadingRecent,
    error,
    archivingId,
    executeSearch,
    clearSearch,
    loadMoreRecent,
    handleArchive,
  } = useSearch();

  const handleSearchSubmit = () => {
    executeSearch(query);
  };

  const isQuerying = searchResult !== null;

  return (
    <View style={styles.root}>
      {/* Header with Search Bar */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.searchBarContainer}>
          <Feather name="search" size={16} color="#8a8d90" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            value={query}
            onChangeText={setQuery}
            placeholder="Search your memories by meaning…"
            placeholderTextColor="#b4b7b9"
            returnKeyType="search"
            onSubmitEditing={handleSearchSubmit}
          />
          {query ? (
            <Pressable onPress={clearSearch} style={styles.clearBtn} hitSlop={8}>
              <Feather name="x" size={14} color="#8a8d90" />
            </Pressable>
          ) : null}
        </View>
        <Pressable
          style={({ pressed }) => [
            styles.searchBtn,
            query.trim().length < 2 && styles.searchBtnDisabled,
            pressed && query.trim().length >= 2 && { opacity: 0.8 },
          ]}
          onPress={handleSearchSubmit}
          disabled={query.trim().length < 2 || searching}
        >
          {searching ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <Text style={styles.searchBtnText}>Search</Text>
          )}
        </Pressable>
        <Pressable
          style={styles.settingsBtn}
          onPress={() => router.push("/settings" as never)}
          hitSlop={8}
        >
          <Feather name="settings" size={18} color={tokens.colors.text} />
        </Pressable>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: insets.bottom + 32 },
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        {/* Query Results View */}
        {isQuerying ? (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionLabel}>
                SEARCH RESULTS ({searchResult.returned_count})
              </Text>
              <Pressable onPress={clearSearch}>
                <Text style={styles.clearResultsText}>Clear search</Text>
              </Pressable>
            </View>

            {searchResult.results.length === 0 ? (
              <View style={styles.emptyWrap}>
                <Text style={styles.emptyTitle}>No matching memories</Text>
                <Text style={styles.emptySub}>
                  No saved memories matched your search for &quot;{searchResult.query}&quot;. Try capturing more ideas or phrasing your search differently.
                </Text>
              </View>
            ) : (
              <View style={styles.cardList}>
                {searchResult.results.map((item) => (
                  <View key={item.memory_id} style={styles.memoryCard}>
                    <View style={styles.cardTopRow}>
                      <View style={styles.typeBadge}>
                        <Text style={styles.typeBadgeText}>
                          {memoryTypeLabel(item.memory_type)}
                        </Text>
                      </View>
                      <Text style={styles.scoreText}>
                        {Math.round(item.similarity_score * 100)}% match
                      </Text>
                    </View>

                    <Text style={styles.cardContent}>{item.content}</Text>

                    {item.source_title ? (
                      <View style={styles.sourceRow}>
                        <Feather name="file-text" size={11} color="#8a8d90" />
                        <Text style={styles.sourceTitleText} numberOfLines={1}>
                          {item.source_title}
                        </Text>
                      </View>
                    ) : null}
                  </View>
                ))}
              </View>
            )}
          </View>
        ) : (
          /* Recent Memory Stream View */
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>RECENT MEMORIES</Text>

            {loadingRecent && recent.length === 0 ? (
              <View style={styles.loadingWrap}>
                <ActivityIndicator size="small" color={tokens.colors.text} />
              </View>
            ) : recent.length === 0 ? (
              <View style={styles.emptyWrap}>
                <Text style={styles.emptyTitle}>No memories yet</Text>
                <Text style={styles.emptySub}>
                  Drop in your first note or URL using the Capture button to start building your memory layer.
                </Text>
              </View>
            ) : (
              <View style={styles.cardList}>
                {recent.map((item) => (
                  <View key={item.memory_id} style={styles.memoryCard}>
                    <View style={styles.cardTopRow}>
                      <View style={styles.badgeGroup}>
                        <View style={styles.typeBadge}>
                          <Text style={styles.typeBadgeText}>
                            {memoryTypeLabel(item.memory_type)}
                          </Text>
                        </View>
                        <Text style={styles.dateText}>
                          {formatDate(item.created_at)}
                        </Text>
                      </View>
                      <Pressable
                        onPress={() => handleArchive(item.memory_id)}
                        disabled={archivingId === item.memory_id}
                        hitSlop={8}
                        style={styles.archiveBtn}
                      >
                        <Feather name="archive" size={13} color="#9a9d9f" />
                      </Pressable>
                    </View>

                    <Text style={styles.cardContent}>{item.content}</Text>

                    {item.summary ? (
                      <Text style={styles.summaryText}>{item.summary}</Text>
                    ) : null}

                    {item.source_title ? (
                      <View style={styles.sourceRow}>
                        <Feather name="file-text" size={11} color="#8a8d90" />
                        <Text style={styles.sourceTitleText} numberOfLines={1}>
                          {item.source_title}
                        </Text>
                      </View>
                    ) : null}
                  </View>
                ))}

                {recentHasMore ? (
                  <Pressable
                    style={({ pressed }) => [
                      styles.loadMoreBtn,
                      pressed && { opacity: 0.8 },
                    ]}
                    onPress={loadMoreRecent}
                    disabled={loadingRecent}
                  >
                    {loadingRecent ? (
                      <ActivityIndicator size="small" color={tokens.colors.text} />
                    ) : (
                      <Text style={styles.loadMoreText}>Load older memories</Text>
                    )}
                  </Pressable>
                ) : null}
              </View>
            )}
          </View>
        )}
      </ScrollView>
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
    gap: tokens.spacing[2],
    paddingHorizontal: tokens.spacing[4],
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e7e8e9",
    backgroundColor: "#ffffff",
  },
  searchBarContainer: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#f5f6f7",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e1e3e4",
    paddingHorizontal: 10,
    height: 44,
  },
  searchIcon: {
    marginRight: 6,
  },
  searchInput: {
    flex: 1,
    fontSize: 13,
    fontWeight: "400",
    color: tokens.colors.text,
  },
  clearBtn: {
    padding: 4,
  },
  searchBtn: {
    height: 44,
    backgroundColor: tokens.colors.text,
    borderRadius: 10,
    paddingHorizontal: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  searchBtnDisabled: {
    backgroundColor: "#c4c7c9",
  },
  searchBtnText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#ffffff",
  },
  settingsBtn: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },

  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: tokens.spacing[5],
    paddingTop: tokens.spacing[4],
  },

  errorBox: {
    backgroundColor: "#fde8e8",
    borderRadius: 10,
    padding: tokens.spacing[3],
    marginBottom: tokens.spacing[4],
  },
  errorText: {
    fontSize: 12,
    color: tokens.colors.danger,
  },

  section: {
    gap: tokens.spacing[3],
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: "#8a8d90",
    letterSpacing: 0.6,
  },
  clearResultsText: {
    fontSize: 11,
    fontWeight: "700",
    color: tokens.colors.text,
  },

  loadingWrap: {
    paddingVertical: tokens.spacing[8],
    alignItems: "center",
  },
  emptyWrap: {
    paddingVertical: tokens.spacing[8],
    alignItems: "center",
    gap: 8,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: tokens.colors.text,
  },
  emptySub: {
    fontSize: 12,
    fontWeight: "400",
    color: tokens.colors.textMuted,
    textAlign: "center",
    lineHeight: 18,
  },

  cardList: {
    gap: tokens.spacing[3],
  },
  memoryCard: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 14,
    padding: tokens.spacing[4],
    backgroundColor: "#ffffff",
    gap: 8,
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 4,
    elevation: 1,
  },
  cardTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  badgeGroup: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  typeBadge: {
    backgroundColor: "#f2f3f4",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  typeBadgeText: {
    fontSize: 10,
    fontWeight: "800",
    color: "#4d5154",
    letterSpacing: 0.3,
  },
  dateText: {
    fontSize: 10,
    fontWeight: "600",
    color: "#9a9d9f",
  },
  scoreText: {
    fontSize: 10,
    fontWeight: "800",
    color: "#2d7058",
  },
  archiveBtn: {
    padding: 4,
  },
  cardContent: {
    fontSize: 13,
    fontWeight: "500",
    color: "#252627",
    lineHeight: 20,
  },
  summaryText: {
    fontSize: 11,
    fontWeight: "400",
    color: "#787c80",
    lineHeight: 16,
  },
  sourceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 2,
  },
  sourceTitleText: {
    fontSize: 10,
    fontWeight: "600",
    color: "#8a8d90",
    flex: 1,
  },

  loadMoreBtn: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fafafa",
    marginTop: 8,
  },
  loadMoreText: {
    fontSize: 12,
    fontWeight: "700",
    color: tokens.colors.text,
  },
});
