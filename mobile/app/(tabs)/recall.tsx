import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
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
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { completeReminder, snoozeReminder, submitQuickRecall as apiSubmitQuickRecall } from "@/api/recalls";
import { BrandMark } from "@/components/shell/BrandMark";
import { StayUpToDateBanner } from "@/components/shell/StayUpToDateBanner";
import { Icons } from "@/components/ui/Icon";

import { MarkdownText } from "@/components/ui/MarkdownText";
import { useRecalls } from "@/hooks/useRecalls";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import type { DueReminder, RecallMemory, RecallQuickAction } from "@/types/api";
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
  const raw = item.memory.source_title || item.memory.human_title || item.memory.summary || item.memory.content;
  return raw
    .replace(/^\*\*(Source|Link|Why you saved this|Key Summary)\*\*:\s*/i, "")
    .replace(/^#{1,6}\s+/, "")
    .replace(/\s*(#[A-Za-z0-9_]+\s*)+$/, "")
    .trim();
}

function itemSubtitle(item: ReadyItem) {
  if (item.kind === "reminder") return formatDue(item.reminder.due_at);
  const created = item.memory.created_at ? new Date(item.memory.created_at) : null;
  const typeName = item.memory.source_type ? item.memory.source_type.toUpperCase() : "MEMORY";
  if (created && !isNaN(created.getTime())) {
    const daysAgo = Math.max(0, Math.floor((Date.now() - created.getTime()) / (1000 * 60 * 60 * 24)));
    const timeAgoStr = daysAgo === 0 ? "Today" : daysAgo === 1 ? "Yesterday" : `${daysAgo} days ago`;
    return `${timeAgoStr} · ${typeName}`;
  }
  return typeName;
}

export default function RecallScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ target_memory_id?: string; memory_id?: string }>();
  const targetMemoryId = params.target_memory_id || params.memory_id;

  const {
    data,
    loading,
    error,
    refresh,
  } = useRecalls(targetMemoryId);

  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh])
  );
  const [activeKey, setActiveKey] = useState<string | null>(null);
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

  const handleQuickAction = async (memory: RecallMemory, action: RecallQuickAction) => {
    if (reminderWorking) return;
    setReminderWorking(true);
    try {
      if (action === "ask_agent") {
        await apiSubmitQuickRecall(memory.memory_id, action);
        closeDetail();
        const rawTitle = memory.human_title || memory.source_title || memory.content;
        const cleanTitle = rawTitle.replace(/^#{1,6}\s+/, "").replace(/\s*(#[A-Za-z0-9_]+\s*)+$/, "").trim();
        let curatedPrompt = `Help me explore and break down key insights from "${cleanTitle}".`;
        if (memory.memory_type === "intention") {
          curatedPrompt = `How can I apply "${cleanTitle}" to what I am building right now?`;
        } else if (memory.memory_type === "action") {
          curatedPrompt = `What is the best way to execute and complete "${cleanTitle}"?`;
        } else if (memory.memory_type === "question") {
          curatedPrompt = `Can you help me answer and resolve "${cleanTitle}"?`;
        }
        router.push(`/(tabs)/?prompt=${encodeURIComponent(curatedPrompt)}&context_memory_id=${memory.memory_id}` as never);
        return;
      }
      await apiSubmitQuickRecall(memory.memory_id, action);
      closeDetail();
      await refresh();
    } catch (err) {
      Alert.alert(
        "Action failed",
        err instanceof Error ? err.message : "Please try again."
      );
    } finally {
      setReminderWorking(false);
    }
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
              working={reminderWorking}
              onQuickAction={(action) => handleQuickAction(activeItem.memory, action)}
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

          <StayUpToDateBanner />
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
  const isPinned = !isReminder && item.memory.pinned_from_notification;
  const label = isReminder
    ? "REMINDER"
    : (item.memory.human_title || memoryTypeLabel(item.memory.memory_type).toUpperCase());
  const title = itemTitle(item);
  const subtitle = itemSubtitle(item);
  const isFirst = index === 0;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.readyRow,
        isFirst && styles.firstReadyRow,
        isPinned && styles.pinnedReadyRow,
        pressed && styles.readyRowPressed,
      ]}
    >
      <View style={[styles.rowIcon, isReminder && styles.reminderIcon, isPinned && styles.pinnedIcon]}>
        {isReminder ? (
          <Icons.Bell size={17} color="#2d7058" />
        ) : (
          <Icons.BookOpenCheck size={17} color={isPinned ? "#d97706" : "#2d7058"} />
        )}
      </View>
      <View style={styles.rowBody}>
        {isPinned ? (
          <View style={styles.pinnedBadge}>
            <Text style={styles.pinnedBadgeText}>🔔 From Today's Nudge</Text>
          </View>
        ) : null}
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
  working,
  onQuickAction,
}: {
  memory: RecallMemory;
  working: boolean;
  onQuickAction: (action: RecallQuickAction) => void;
}) {
  const title = memory.human_title || memory.summary || memory.content;
  const promptText =
    memory.human_prompt ||
    "Do you still want to revisit this memory or take action on it?";

  return (
    <View style={styles.detailBlock}>
      {memory.pinned_from_notification ? (
        <View style={styles.pinnedBadgeLarge}>
          <Text style={styles.pinnedBadgeLargeText}>🔔 Pinned from Notification</Text>
        </View>
      ) : null}

      <View style={styles.detailLabelRow}>
        <Icons.BookOpenCheck size={16} color="#2d7058" />
        <Text style={styles.detailLabel}>{title.toUpperCase()}</Text>
      </View>

      <Text style={styles.detailTitle}>{promptText}</Text>

      <View style={styles.ideaBox}>
        <Text style={styles.ideaLabel}>MEMORY SUMMARY</Text>
        <MarkdownText text={memory.summary || memory.content} />
      </View>

      <View style={styles.checkBox}>
        <Text style={styles.checkLabel}>QUICK ACTIONS</Text>
        <View style={styles.quickGrid3}>
          <Pressable
            style={styles.quickActionButton}
            disabled={working}
            onPress={() => onQuickAction("snooze_7d")}
          >
            <Icons.Clock3 size={18} color="#374151" />
            <Text style={styles.quickActionTitle}>Snooze</Text>
            <Text style={styles.quickActionSub}>1 week</Text>
          </Pressable>

          <Pressable
            style={styles.quickActionButton}
            disabled={working}
            onPress={() => onQuickAction("applied")}
          >
            <Icons.CheckCircle size={18} color="#374151" />
            <Text style={styles.quickActionTitle}>Used it</Text>
            <Text style={styles.quickActionSub}>Completed</Text>
          </Pressable>

          <Pressable
            style={styles.quickActionButton}
            disabled={working}
            onPress={() => onQuickAction("ask_agent")}
          >
            <Icons.MessageCircle size={18} color="#374151" />
            <Text style={styles.quickActionTitle}>Ask Crowscap</Text>
            <Text style={styles.quickActionSub}>Chat context</Text>
          </Pressable>
        </View>
      </View>
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
    fontSize: 19,
    lineHeight: 26,
    fontFamily: fontFamily.bold,
    color: "#111827",
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
    borderColor: "#e5e7eb",
    borderRadius: 12,
    backgroundColor: "#ffffff",
    padding: 18,
    gap: 12,
  },
  checkLabel: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#2d7058",
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
  pinnedReadyRow: {
    backgroundColor: "#fffbeb",
    borderColor: "#fde68a",
    borderWidth: 1.5,
  },
  pinnedIcon: {
    backgroundColor: "#fef3c7",
  },
  pinnedBadge: {
    alignSelf: "flex-start",
    backgroundColor: "#fef3c7",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    marginBottom: 4,
  },
  pinnedBadgeText: {
    fontSize: 11,
    fontFamily: fontFamily.bold,
    color: "#b45309",
  },
  pinnedBadgeLarge: {
    backgroundColor: "#fef3c7",
    borderColor: "#fde68a",
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    alignSelf: "flex-start",
    marginBottom: 12,
  },
  pinnedBadgeLargeText: {
    fontSize: 12,
    fontFamily: fontFamily.bold,
    color: "#b45309",
  },
  quickGrid3: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  quickActionButton: {
    flex: 1,
    backgroundColor: "#ffffff",
    borderColor: "#e5e7eb",
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 6,
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
  },
  quickActionTitle: {
    fontSize: 12.5,
    fontFamily: fontFamily.bold,
    color: "#111827",
    textAlign: "center",
  },
  quickActionSub: {
    fontSize: 10,
    fontFamily: fontFamily.medium,
    color: "#2d7058",
    textAlign: "center",
  },
});

