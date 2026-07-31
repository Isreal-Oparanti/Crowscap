import { useMemo, useState } from "react";
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
import { completeReminder, snoozeReminder } from "@/api/recalls";
import { BrandMark } from "@/components/shell/BrandMark";
import { Icons } from "@/components/ui/Icon";
import { MarkdownText } from "@/components/ui/MarkdownText";
import { useRecalls } from "@/hooks/useRecalls";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import type { DueReminder, RecallMemory } from "@/types/api";
import { formatOverdue, memoryTypeLabel, truncate } from "@/utils/format";
import { scheduleLocalNotification } from "@/utils/notifications";


type ReadyItem =
  | { kind: "reminder"; id: string; reminder: DueReminder }
  | { kind: "memory"; id: string; memory: RecallMemory };

function formatDue(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Due now";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function itemKey(item: ReadyItem) {
  return `${item.kind}:${item.id}`;
}

function itemTitle(item: ReadyItem) {
  if (item.kind === "reminder") return item.reminder.content;
  return item.memory.summary || item.memory.content;
}

function itemSubtitle(item: ReadyItem) {
  if (item.kind === "reminder") return formatDue(item.reminder.due_at);
  return item.memory.source_title || "Saved memory";
}

export default function RecallScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const {
    data,
    loading,
    error,
    answering,
    evaluation,
    submitAnswerFor,
    refresh,
  } = useRecalls();
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [writtenAnswer, setWrittenAnswer] = useState("");
  const [reminderWorking, setReminderWorking] = useState(false);

  const readyItems = useMemo<ReadyItem[]>(() => {
    const reminders = (data?.reminders ?? []).map((reminder) => ({
      kind: "reminder" as const,
      id: reminder.reminder_id,
      reminder,
    }));
    const memories = (data?.memories ?? []).map((memory) => ({
      kind: "memory" as const,
      id: memory.memory_id,
      memory,
    }));
    return [...reminders, ...memories];
  }, [data]);

  const activeItem = readyItems.find((item) => itemKey(item) === activeKey) ?? null;

  const closeDetail = () => {
    setActiveKey(null);
    setWrittenAnswer("");
  };

  const completeActiveReminder = async (reminderId: string) => {
    if (reminderWorking) return;
    setReminderWorking(true);
    try {
      await completeReminder(reminderId);
      closeDetail();
      await refresh();
    } catch (err) {
      Alert.alert(
        "Could not finish reminder",
        err instanceof Error ? err.message : "Please try again."
      );
    } finally {
      setReminderWorking(false);
    }
  };

  const snoozeActiveReminder = async (reminderId: string) => {
    if (reminderWorking) return;
    setReminderWorking(true);
    try {
      await snoozeReminder(reminderId, 60);
      closeDetail();
      await refresh();
    } catch (err) {
      Alert.alert(
        "Could not snooze reminder",
        err instanceof Error ? err.message : "Please try again."
      );
    } finally {
      setReminderWorking(false);
    }
  };

  const submitQuickRecall = async (memory: RecallMemory, answer: string, rating: number) => {
    await submitAnswerFor(memory.memory_id, answer, rating);
    setWrittenAnswer("");
  };

  if (loading) {
    return (
      <View style={styles.root}>
        <Header onSettings={() => router.push("/settings" as never)} />
        <View style={styles.centered}>
          <ActivityIndicator size="small" color={tokens.colors.text} />
          <Text style={styles.mutedText}>Checking what is ready.</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.root}>
        <Header onSettings={() => router.push("/settings" as never)} />
        <View style={styles.centered}>
          <Text style={styles.errorTitle}>Recall could not load</Text>
          <Text style={styles.errorBody}>{error}</Text>
          <Pressable style={styles.primaryButton} onPress={refresh}>
            <Text style={styles.primaryButtonText}>Try again</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <Header onSettings={() => router.push("/settings" as never)} />
      {activeItem ? (
        <ScrollView
          style={styles.content}
          contentContainerStyle={[styles.detailContent, { paddingBottom: insets.bottom + 108 }]}
          showsVerticalScrollIndicator={false}
        >
          <Pressable style={styles.backRow} onPress={closeDetail}>
            <Icons.ArrowLeft size={18} color={tokens.colors.text} />
            <Text style={styles.backText}>All ready items</Text>
          </Pressable>

          {activeItem.kind === "reminder" ? (
            <ReminderDetail
              reminder={activeItem.reminder}
              working={reminderWorking}
              onDone={() => completeActiveReminder(activeItem.reminder.reminder_id)}
              onSnooze={() => snoozeActiveReminder(activeItem.reminder.reminder_id)}
            />
          ) : (
            <MemoryDetail
              memory={activeItem.memory}
              answering={answering}
              evaluation={evaluation}
              answer={writtenAnswer}
              onChangeAnswer={setWrittenAnswer}
              onQuickAnswer={(answer, rating) =>
                submitQuickRecall(activeItem.memory, answer, rating)
              }
              onSubmit={() =>
                submitQuickRecall(
                  activeItem.memory,
                  writtenAnswer.trim() || "I reviewed this memory.",
                  4
                )
              }
            />
          )}
        </ScrollView>
      ) : (
        <ScrollView
          style={styles.content}
          contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom + 96 }]}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.hero}>
            <Text style={styles.eyebrow}>READY NOW</Text>
            <Text style={styles.heroTitle}>Choose what to revisit.</Text>
          </View>

          {readyItems.length === 0 ? (
            <View style={styles.emptyState}>
              <Icons.Clock3 size={20} color={tokens.colors.textMuted} />
              <Text style={styles.emptyTitle}>Nothing ready right now.</Text>
              <Text style={styles.emptyBody}>
                Crowscap will bring back a memory when it is useful again.
              </Text>
              <Pressable
                style={styles.testNotifButton}
                onPress={async () => {
                  const scheduled = await scheduleLocalNotification({
                    title: "Crowscap Reminder",
                    body: "Time to revisit your saved memory about distribution strategy!",
                    url: "/(tabs)/recall",
                    seconds: 5,
                  });
                  if (scheduled) {
                    Alert.alert("Reminder Scheduled!", "Minimize or lock your screen—you will get a notification in 5 seconds.");
                  } else {
                    Alert.alert("Permission Required", "Please grant notification permissions in system settings.");
                  }
                }}
              >
                <Icons.Bell size={14} color="#2d7058" />
                <Text style={styles.testNotifText}>Test 5s Local Reminder Notification</Text>
              </Pressable>
            </View>
          ) : (
            <View style={styles.readyList}>
              {readyItems.map((item, index) => (
                <ReadyRow
                  key={itemKey(item)}
                  item={item}
                  index={index}
                  onPress={() => setActiveKey(itemKey(item))}
                />
              ))}
            </View>
          )}

        </ScrollView>
      )}
    </View>
  );

}

function Header({ onSettings }: { onSettings: () => void }) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data: recallData } = useRecalls();
  const hasUnreadRecalls = (recallData?.memories?.length ?? 0) > 0;

  return (
    <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
      <View style={styles.headerBrand}>
        <BrandMark size={38} imageSize={29} />
        <View>
          <Text style={styles.headerTitle}>Recall</Text>
          <Text style={styles.headerSub}>Ready items</Text>
        </View>
      </View>
      <View style={styles.headerActions}>
        <Pressable onPress={() => router.push("/(tabs)/recall" as never)} hitSlop={8} style={styles.iconButton}>
          <Icons.Bell size={19} color={tokens.colors.text} />
          {hasUnreadRecalls ? <View style={styles.bellDot} /> : null}
        </Pressable>
        <Pressable onPress={onSettings} hitSlop={8} style={styles.iconButton}>
          <Icons.Settings size={19} color={tokens.colors.text} />
        </Pressable>
      </View>
    </View>
  );
}


function ReadyRow({ item, index, onPress }: { item: ReadyItem; index: number; onPress: () => void }) {
  const isReminder = item.kind === "reminder";
  const label = isReminder ? "REMINDER" : memoryTypeLabel(item.memory.memory_type).toUpperCase();
  const title = itemTitle(item);
  const subtitle = itemSubtitle(item);
  const isFirst = index === 0;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.readyRow,
        isFirst && styles.firstReadyRow,
        pressed && styles.readyRowPressed,
      ]}
    >
      <View style={[styles.rowIcon, isReminder && styles.reminderIcon]}>
        {isReminder ? (
          <Icons.Bell size={17} color="#2d7058" />
        ) : (
          <Icons.BookOpenCheck size={17} color="#2d7058" />
        )}
      </View>
      <View style={styles.rowBody}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowTitle} numberOfLines={2}>
          {title}
        </Text>
        <Text style={styles.rowSubtitle} numberOfLines={1}>
          {subtitle}
        </Text>
      </View>
      <Icons.ChevronRight size={16} color="#9fa3a7" />
    </Pressable>
  );
}


function ReminderDetail({
  reminder,
  working,
  onDone,
  onSnooze,
}: {
  reminder: DueReminder;
  working: boolean;
  onDone: () => void;
  onSnooze: () => void;
}) {
  return (
    <View style={styles.detailBlock}>
      <View style={styles.detailLabelRow}>
        <Icons.Bell size={17} color="#2f7b60" />
        <Text style={styles.detailLabel}>REMINDER READY</Text>
      </View>
      <Text style={styles.detailTitle}>{reminder.content}</Text>
      <Text style={styles.detailMeta}>
        Due {formatDue(reminder.due_at)} - {formatOverdue(reminder.overdue_seconds)}
      </Text>

      <View style={styles.noticeBox}>
        <Text style={styles.noticeTitle}>ONE-TIME REMINDER</Text>
        <Text style={styles.noticeText}>
          Mark it done and it leaves the active recall surface.
        </Text>
      </View>

      <View style={styles.actionRow}>
        <Pressable style={styles.outlineButton} onPress={onDone} disabled={working}>
          {working ? (
            <ActivityIndicator size="small" color="#2f7b60" />
          ) : (
            <>
              <Icons.CheckCircle size={17} color="#2f7b60" />
              <Text style={styles.outlineButtonText}>Done</Text>
            </>
          )}
        </Pressable>
        <Pressable style={styles.outlineButton} onPress={onSnooze} disabled={working}>
          <Icons.Clock3 size={17} color="#596066" />
          <Text style={styles.outlineButtonText}>Snooze 1h</Text>
        </Pressable>
      </View>
    </View>
  );
}

function MemoryDetail({
  memory,
  answering,
  evaluation,
  answer,
  onChangeAnswer,
  onQuickAnswer,
  onSubmit,
}: {
  memory: RecallMemory;
  answering: boolean;
  evaluation: ReturnType<typeof useRecalls>["evaluation"];
  answer: string;
  onChangeAnswer: (value: string) => void;
  onQuickAnswer: (answer: string, rating: number) => void;
  onSubmit: () => void;
}) {
  const title = memory.summary || memory.content;

  return (
      <View style={styles.detailBlock}>
        <View style={styles.detailLabelRow}>
        <Icons.BookOpenCheck size={17} color="#2f7b60" />
        <Text style={styles.detailLabel}>A THOUGHT IS READY</Text>
      </View>
      <Text style={styles.detailTitle}>{title}</Text>
      <Text style={styles.detailMeta}>
        {memory.source_title || "Saved memory"} - {formatOverdue(memory.overdue_seconds)}
      </Text>

      <View style={styles.ideaBox}>
        <Text style={styles.ideaLabel}>THE IDEA</Text>
        <MarkdownText text={memory.content} compact />
      </View>

      {memory.epistemic_label ? (
        <View style={styles.warningBox}>
          <Icons.CircleAlert size={14} color="#9b6a24" />
          <Text style={styles.warningText}>
            Saved as {memory.epistemic_label.replace("_", " ")}, not as verified fact.
          </Text>
        </View>
      ) : null}

      <View style={styles.checkBox}>
        <Text style={styles.checkLabel}>QUICK CHECK</Text>
        <Text style={styles.checkQuestion}>
          Does this still feel useful for what you are doing now?
        </Text>
        <View style={styles.quickGrid}>
          <Pressable
            style={styles.quickButton}
            disabled={answering}
            onPress={() => onQuickAnswer("This is still useful.", 5)}
          >
            <Text style={styles.quickButtonText}>Still useful</Text>
          </Pressable>
          <Pressable
            style={styles.quickButton}
            disabled={answering}
            onPress={() => onQuickAnswer("I used this memory.", 5)}
          >
            <Text style={styles.quickButtonText}>I used it</Text>
          </Pressable>
          <Pressable
            style={styles.quickButton}
            disabled={answering}
            onPress={() => onQuickAnswer("Not now.", 2)}
          >
            <Text style={styles.quickButtonText}>Not now</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.answerBox}>
        <Text style={styles.checkLabel}>REVIEW DEEPER</Text>
        <TextInput
          value={answer}
          onChangeText={onChangeAnswer}
          multiline
          placeholder="Write what changed, what you used, or what still feels unclear."
          placeholderTextColor="#9b9fa4"
          style={styles.answerInput}
          textAlignVertical="top"
        />
        <Pressable
          style={[styles.primaryButton, (!answer.trim() || answering) && styles.disabledButton]}
          disabled={!answer.trim() || answering}
          onPress={onSubmit}
        >
          {answering ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <Text style={styles.primaryButtonText}>Save review</Text>
          )}
        </Pressable>
      </View>

      {evaluation ? (
        <View style={styles.evaluationBox}>
          <Text style={styles.evaluationTitle}>Review saved</Text>
          <MarkdownText text={evaluation.feedback} compact />
        </View>
      ) : null}
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
    backgroundColor: "#ffffff",
  },
  listContent: {
    paddingTop: 0,
  },
  detailContent: {
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  hero: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 18,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f1f3",
  },
  eyebrow: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#787c80",
    marginBottom: 6,
    letterSpacing: 0.5,
  },
  heroTitle: {
    fontSize: 24,
    lineHeight: 30,
    fontFamily: fontFamily.bold,
    color: "#111418",
  },
  readyList: {
    backgroundColor: "#ffffff",
  },
  readyRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f1f3",
    backgroundColor: "#ffffff",
  },
  firstReadyRow: {
    backgroundColor: "#f1f7f4",
  },
  readyRowPressed: {
    backgroundColor: "#eaf5ef",
  },
  rowIcon: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#e8f4ed",
  },
  reminderIcon: {
    backgroundColor: "#fff7df",
  },
  rowBody: {
    flex: 1,
    gap: 3,
  },
  rowLabel: {
    fontSize: 10.5,
    fontFamily: fontFamily.extrabold,
    color: "#787c80",
    letterSpacing: 0.5,
  },
  rowTitle: {
    fontSize: 14.5,
    lineHeight: 20,
    color: "#111418",
    fontFamily: fontFamily.bold,
  },
  rowSubtitle: {
    fontSize: 12,
    color: "#8a8e94",
    fontFamily: fontFamily.medium,
  },

  backRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    alignSelf: "flex-start",
    marginBottom: 26,
  },
  backText: {
    fontSize: 14,
    color: tokens.colors.text,
    fontFamily: fontFamily.extrabold,
  },
  detailBlock: {
    gap: 18,
  },
  detailLabelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
  },
  detailLabel: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#2f7b60",
  },
  detailTitle: {
    fontSize: 30,
    lineHeight: 36,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  detailMeta: {
    marginTop: -8,
    fontSize: 13,
    lineHeight: 18,
    color: tokens.colors.textMuted,
    fontFamily: fontFamily.semibold,
  },
  noticeBox: {
    borderWidth: 1,
    borderColor: "#c9e0d3",
    borderRadius: 10,
    backgroundColor: "#f1faf5",
    padding: 18,
    gap: 8,
  },
  noticeTitle: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#2f7b60",
  },
  noticeText: {
    fontSize: 15,
    lineHeight: 22,
    color: "#355447",
    fontFamily: fontFamily.medium,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    flexWrap: "wrap",
  },
  outlineButton: {
    minHeight: 52,
    minWidth: 118,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: "#d5dadd",
    borderRadius: 10,
    paddingHorizontal: 16,
    backgroundColor: "#ffffff",
  },
  outlineButtonText: {
    fontSize: 16,
    color: "#373b3f",
    fontFamily: fontFamily.bold,
  },
  ideaBox: {
    borderWidth: 1,
    borderColor: "#dfe3e5",
    borderRadius: 12,
    backgroundColor: "#ffffff",
    padding: 18,
    gap: 10,
  },
  ideaLabel: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#7a7d82",
  },
  warningBox: {
    flexDirection: "row",
    gap: 9,
    borderWidth: 1,
    borderColor: "#eed8ae",
    borderRadius: 10,
    backgroundColor: "#fff8eb",
    padding: 14,
  },
  warningText: {
    flex: 1,
    fontSize: 12,
    lineHeight: 17,
    color: "#8a641f",
    fontFamily: fontFamily.semibold,
  },
  checkBox: {
    borderWidth: 1,
    borderColor: "#c9e0d3",
    borderRadius: 12,
    backgroundColor: "#f1faf5",
    padding: 18,
    gap: 12,
  },
  checkLabel: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#2f7b60",
  },
  checkQuestion: {
    fontSize: 15,
    lineHeight: 22,
    color: "#355447",
    fontFamily: fontFamily.semibold,
  },
  quickGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  quickButton: {
    borderWidth: 1,
    borderColor: "#d5dadd",
    borderRadius: 8,
    backgroundColor: "#ffffff",
    paddingHorizontal: 13,
    paddingVertical: 11,
  },
  quickButtonText: {
    fontSize: 14,
    color: "#3f4347",
    fontFamily: fontFamily.bold,
  },
  answerBox: {
    gap: 10,
  },
  answerInput: {
    minHeight: 110,
    borderWidth: 1,
    borderColor: "#d8dcdf",
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    lineHeight: 21,
    fontFamily: fontFamily.medium,
    color: tokens.colors.text,
    backgroundColor: "#ffffff",
  },
  primaryButton: {
    minHeight: 48,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#111111",
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 14,
    fontFamily: fontFamily.extrabold,
  },
  disabledButton: {
    backgroundColor: "#c9cccf",
  },
  evaluationBox: {
    borderWidth: 1,
    borderColor: "#dbe7df",
    borderRadius: 12,
    backgroundColor: "#f8fcfa",
    padding: 16,
    gap: 10,
  },
  evaluationTitle: {
    fontSize: 13,
    color: "#2f7b60",
    fontFamily: fontFamily.extrabold,
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
    gap: 12,
  },
  mutedText: {
    fontSize: 13,
    color: tokens.colors.textMuted,
    fontFamily: fontFamily.semibold,
  },
  errorTitle: {
    fontSize: 18,
    color: tokens.colors.text,
    fontFamily: fontFamily.extrabold,
  },
  errorBody: {
    fontSize: 13,
    color: tokens.colors.textMuted,
    textAlign: "center",
    lineHeight: 19,
  },
  emptyState: {
    paddingHorizontal: 24,
    paddingTop: 52,
    alignItems: "center",
    gap: 10,
  },
  emptyTitle: {
    fontSize: 19,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  emptyBody: {
    fontSize: 14,
    color: tokens.colors.textMuted,
    lineHeight: 20,
    textAlign: "center",
  },
  testNotifButton: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: "#e8f4ed",
    borderWidth: 1,
    borderColor: "#cbe5d5",
  },
  testNotifText: {
    fontSize: 13,
    fontFamily: fontFamily.bold,
    color: "#2d7058",
  },
});

