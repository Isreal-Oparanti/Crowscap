import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useState } from "react";
import { useRecalls } from "@/hooks/useRecalls";
import { memoryTypeLabel, formatOverdue } from "@/utils/format";
import { tokens } from "@/theme/tokens";

export default function RecallScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const {
    data,
    loading,
    error,
    selectedMemory,
    selectedId,
    setSelectedId,
    answering,
    evaluation,
    submitAnswer,
    nextRecall,
    refresh,
  } = useRecalls();

  const [answerText, setAnswerText] = useState("");
  const [rating, setRating] = useState(3);

  const handleSubmit = async () => {
    if (!answerText.trim() || answering) return;
    await submitAnswer(answerText.trim(), rating);
    setAnswerText("");
  };

  const dueCount = data?.due_count ?? 0;

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerTitleRow}>
          <Text style={styles.headerTitle}>Recall</Text>
          {dueCount > 0 ? (
            <View style={styles.readyBadge}>
              <View style={styles.readyDot} />
              <Text style={styles.readyText}>{dueCount} Ready</Text>
            </View>
          ) : (
            <Text style={styles.headerSub}>Active review queue</Text>
          )}
        </View>
        <View style={styles.headerActions}>
          <Pressable onPress={refresh} style={styles.refreshBtn} hitSlop={8}>
            <Feather name="refresh-cw" size={16} color="#777a7e" />
          </Pressable>
          <Pressable onPress={() => router.push("/settings" as never)} style={styles.refreshBtn} hitSlop={8}>
            <Feather name="settings" size={18} color={tokens.colors.text} />
          </Pressable>
        </View>
      </View>

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="small" color={tokens.colors.text} />
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={refresh} style={styles.retryBtn}>
            <Text style={styles.retryBtnText}>Retry</Text>
          </Pressable>
        </View>
      ) : !selectedMemory || dueCount === 0 ? (
        <View style={styles.centered}>
          <View style={styles.emptyIcon}>
            <Feather name="check-circle" size={32} color="#2d7058" />
          </View>
          <Text style={styles.emptyTitle}>All caught up!</Text>
          <Text style={styles.emptySub}>
            No due recall prompts right now. Crowscap will notify you when your next memory is ready for review.
          </Text>
        </View>
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={[
            styles.scrollContent,
            { paddingBottom: insets.bottom + 32 },
          ]}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* Queue selector */}
          {data && data.memories.length > 1 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.queueBar}
            >
              {data.memories.map((m, idx) => {
                const active = m.memory_id === selectedId;
                return (
                  <Pressable
                    key={m.memory_id}
                    style={[styles.queueChip, active && styles.queueChipActive]}
                    onPress={() => setSelectedId(m.memory_id)}
                  >
                    <Text
                      style={[
                        styles.queueChipText,
                        active && styles.queueChipTextActive,
                      ]}
                    >
                      Prompt {idx + 1}
                    </Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          ) : null}

          {/* Active Recall Card */}
          <View style={styles.recallCard}>
            <View style={styles.cardHeader}>
              <View style={styles.badgeRow}>
                <View style={styles.typeBadge}>
                  <Text style={styles.typeBadgeText}>
                    {memoryTypeLabel(selectedMemory.memory_type)}
                  </Text>
                </View>
                <View
                  style={[
                    styles.confidenceDot,
                    styles[`conf_${selectedMemory.confidence}`],
                  ]}
                />
                <Text style={styles.confidenceLabel}>
                  {selectedMemory.confidence}
                </Text>
              </View>

              {selectedMemory.overdue_seconds > 0 ? (
                <View style={styles.overdueBadge}>
                  <Feather name="clock" size={10} color="#b07030" />
                  <Text style={styles.overdueText}>
                    {formatOverdue(selectedMemory.overdue_seconds)}
                  </Text>
                </View>
              ) : null}
            </View>

            {/* Prompt Question */}
            <Text style={styles.questionPrompt}>
              How would you explain or apply this memory in your own words?
            </Text>

            {/* Memory Content Box */}
            <View style={styles.memoryBox}>
              <Text style={styles.memoryContentText}>
                {selectedMemory.content}
              </Text>
              {selectedMemory.source_title ? (
                <Text style={styles.sourceTitle}>
                  Source: {selectedMemory.source_title}
                </Text>
              ) : null}
            </View>
          </View>

          {/* Evaluation result if completed */}
          {evaluation ? (
            <View style={styles.evalCard}>
              <View style={styles.evalHeader}>
                <View style={styles.evalScoreBadge}>
                  <Text style={styles.evalScoreText}>
                    Score: {Math.round(evaluation.score * 100)}%
                  </Text>
                </View>
                <Text style={styles.evalRatingLabel}>
                  {evaluation.rating.toUpperCase()}
                </Text>
              </View>

              <Text style={styles.evalFeedback}>{evaluation.feedback}</Text>

              {evaluation.understanding_summary ? (
                <View style={styles.evalSummaryBox}>
                  <Text style={styles.evalSectionTitle}>UNDERSTANDING</Text>
                  <Text style={styles.evalSummaryText}>
                    {evaluation.understanding_summary}
                  </Text>
                </View>
              ) : null}

              {evaluation.knowledge_gaps.length > 0 ? (
                <View style={styles.evalGapBox}>
                  <Text style={styles.evalGapTitle}>KNOWLEDGE GAPS</Text>
                  {evaluation.knowledge_gaps.map((gap, i) => (
                    <Text key={i} style={styles.evalGapText}>
                      • {gap}
                    </Text>
                  ))}
                </View>
              ) : null}

              {evaluation.next_question ? (
                <View style={styles.nextQuestionBox}>
                  <Text style={styles.evalSectionTitle}>DEEPER QUESTION</Text>
                  <Text style={styles.nextQuestionText}>
                    {evaluation.next_question}
                  </Text>
                </View>
              ) : null}

              <Pressable style={styles.nextBtn} onPress={nextRecall}>
                <Text style={styles.nextBtnText}>Next prompt</Text>
                <Feather name="arrow-right" size={16} color="#ffffff" />
              </Pressable>
            </View>
          ) : (
            /* Answer Form */
            <View style={styles.formCard}>
              <Text style={styles.formLabel}>YOUR ANSWER</Text>
              <TextInput
                style={styles.answerInput}
                value={answerText}
                onChangeText={setAnswerText}
                placeholder="Explain the key idea, or how you would use it..."
                placeholderTextColor="#b4b7b9"
                multiline
                numberOfLines={4}
                textAlignVertical="top"
              />

              {/* Rating 1 - 5 */}
              <Text style={styles.formLabel}>HOW WELL DID YOU REMEMBER THIS?</Text>
              <View style={styles.ratingRow}>
                {[1, 2, 3, 4, 5].map((val) => (
                  <Pressable
                    key={val}
                    style={[
                      styles.ratingBtn,
                      rating === val && styles.ratingBtnActive,
                    ]}
                    onPress={() => setRating(val)}
                  >
                    <Text
                      style={[
                        styles.ratingBtnText,
                        rating === val && styles.ratingBtnTextActive,
                      ]}
                    >
                      {val}
                    </Text>
                  </Pressable>
                ))}
              </View>
              <View style={styles.ratingScaleLabels}>
                <Text style={styles.scaleText}>1 (Vague)</Text>
                <Text style={styles.scaleText}>5 (Perfect)</Text>
              </View>

              <Pressable
                style={({ pressed }) => [
                  styles.submitBtn,
                  (!answerText.trim() || answering) && styles.submitBtnDisabled,
                  pressed && answerText.trim() && { opacity: 0.85 },
                ]}
                onPress={handleSubmit}
                disabled={!answerText.trim() || answering}
              >
                {answering ? (
                  <ActivityIndicator size="small" color="#ffffff" />
                ) : (
                  <>
                    <Text style={styles.submitBtnText}>Evaluate answer</Text>
                    <Feather name="send" size={14} color="#ffffff" />
                  </>
                )}
              </Pressable>
            </View>
          )}
        </ScrollView>
      )}
    </KeyboardAvoidingView>
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
    paddingHorizontal: tokens.spacing[5],
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e7e8e9",
    backgroundColor: "#ffffff",
  },
  headerTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[3],
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: tokens.colors.text,
    letterSpacing: -0.3,
  },
  headerSub: {
    fontSize: 11,
    fontWeight: "500",
    color: tokens.colors.textMuted,
  },
  readyBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: "#eaf3ee",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
  },
  readyDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#2d7058",
  },
  readyText: {
    fontSize: 10,
    fontWeight: "800",
    color: "#2d7058",
    letterSpacing: 0.3,
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  refreshBtn: {
    padding: 6,
  },

  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: tokens.spacing[6],
    gap: tokens.spacing[3],
  },
  errorText: {
    fontSize: 13,
    color: tokens.colors.danger,
    textAlign: "center",
  },
  retryBtn: {
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  retryBtnText: {
    fontSize: 12,
    fontWeight: "600",
    color: tokens.colors.text,
  },
  emptyIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#edf5f1",
    alignItems: "center",
    justifyContent: "center",
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: tokens.colors.text,
  },
  emptySub: {
    fontSize: 13,
    fontWeight: "400",
    color: tokens.colors.textMuted,
    textAlign: "center",
    lineHeight: 20,
  },

  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: tokens.spacing[5],
    paddingTop: tokens.spacing[4],
    gap: tokens.spacing[5],
  },

  queueBar: {
    gap: 8,
    paddingBottom: 4,
  },
  queueChip: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: tokens.radius.full,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: "#fafafa",
  },
  queueChipActive: {
    backgroundColor: tokens.colors.text,
    borderColor: tokens.colors.text,
  },
  queueChipText: {
    fontSize: 11,
    fontWeight: "700",
    color: "#555860",
  },
  queueChipTextActive: {
    color: "#ffffff",
  },

  recallCard: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 16,
    padding: tokens.spacing[4],
    backgroundColor: "#ffffff",
    gap: tokens.spacing[3],
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  badgeRow: {
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
    fontWeight: "800",
    color: "#4d5154",
    letterSpacing: 0.3,
  },
  confidenceDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginLeft: 2,
  },
  conf_high: { backgroundColor: "#2d7058" },
  conf_medium: { backgroundColor: "#b07030" },
  conf_low: { backgroundColor: "#9b4c51" },
  conf_unknown: { backgroundColor: "#b4b7b9" },
  confidenceLabel: {
    fontSize: 10,
    fontWeight: "600",
    color: "#8a8d90",
  },
  overdueBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "#fff6eb",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  overdueText: {
    fontSize: 10,
    fontWeight: "700",
    color: "#b07030",
  },
  questionPrompt: {
    fontSize: 15,
    fontWeight: "800",
    color: tokens.colors.text,
    lineHeight: 22,
    letterSpacing: -0.2,
  },
  memoryBox: {
    backgroundColor: "#fafafa",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e8eaec",
    padding: tokens.spacing[3],
    gap: 6,
  },
  memoryContentText: {
    fontSize: 13,
    fontWeight: "500",
    color: "#252627",
    lineHeight: 20,
  },
  sourceTitle: {
    fontSize: 10,
    fontWeight: "600",
    color: "#8a8d90",
  },

  formCard: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    borderRadius: 16,
    padding: tokens.spacing[4],
    backgroundColor: "#ffffff",
    gap: tokens.spacing[3],
  },
  formLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: "#8a8d90",
    letterSpacing: 0.6,
  },
  answerInput: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: 12,
    padding: tokens.spacing[3],
    fontSize: 13,
    fontWeight: "400",
    color: tokens.colors.text,
    lineHeight: 20,
    minHeight: 96,
    backgroundColor: "#fafafa",
    textAlignVertical: "top",
  },
  ratingRow: {
    flexDirection: "row",
    gap: 8,
  },
  ratingBtn: {
    flex: 1,
    height: 40,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#e1e3e4",
    backgroundColor: "#fafafa",
    alignItems: "center",
    justifyContent: "center",
  },
  ratingBtnActive: {
    backgroundColor: tokens.colors.text,
    borderColor: tokens.colors.text,
  },
  ratingBtnText: {
    fontSize: 14,
    fontWeight: "800",
    color: "#4d5154",
  },
  ratingBtnTextActive: {
    color: "#ffffff",
  },
  ratingScaleLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: -4,
  },
  scaleText: {
    fontSize: 10,
    fontWeight: "500",
    color: "#9a9d9f",
  },
  submitBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 48,
    borderRadius: 12,
    backgroundColor: tokens.colors.text,
    marginTop: 4,
  },
  submitBtnDisabled: {
    backgroundColor: "#c4c7c9",
  },
  submitBtnText: {
    fontSize: 13,
    fontWeight: "800",
    color: "#ffffff",
  },

  evalCard: {
    borderWidth: 1,
    borderColor: "#d7e9df",
    borderRadius: 16,
    padding: tokens.spacing[4],
    backgroundColor: "#f4fdf8",
    gap: tokens.spacing[3],
  },
  evalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  evalScoreBadge: {
    backgroundColor: "#2d7058",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  evalScoreText: {
    fontSize: 12,
    fontWeight: "800",
    color: "#ffffff",
  },
  evalRatingLabel: {
    fontSize: 11,
    fontWeight: "800",
    color: "#2d7058",
    letterSpacing: 0.5,
  },
  evalFeedback: {
    fontSize: 13,
    fontWeight: "500",
    color: "#1c3d31",
    lineHeight: 20,
  },
  evalSectionTitle: {
    fontSize: 10,
    fontWeight: "800",
    color: "#2d7058",
    letterSpacing: 0.6,
  },
  evalSummaryBox: {
    gap: 4,
  },
  evalSummaryText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#285b48",
    lineHeight: 18,
  },
  evalGapBox: {
    gap: 4,
  },
  evalGapTitle: {
    fontSize: 10,
    fontWeight: "800",
    color: "#b07030",
    letterSpacing: 0.6,
  },
  evalGapText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#754b20",
    lineHeight: 18,
  },
  nextQuestionBox: {
    gap: 4,
    borderTopWidth: 1,
    borderTopColor: "#d7e9df",
    paddingTop: 8,
  },
  nextQuestionText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#1c3d31",
    lineHeight: 20,
  },
  nextBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 46,
    borderRadius: 10,
    backgroundColor: "#2d7058",
    marginTop: 4,
  },
  nextBtnText: {
    fontSize: 13,
    fontWeight: "800",
    color: "#ffffff",
  },
});
