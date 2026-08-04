import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type ListRenderItem,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as DocumentPicker from "expo-document-picker";
import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { useRouter } from "expo-router";

import { sendChatMessage, getCurrentConversation } from "@/api/chat";
import { capturePdf } from "@/api/captures";

import { BrandMark } from "@/components/shell/BrandMark";
import { Icons } from "@/components/ui/Icon";
import { MarkdownText } from "@/components/ui/MarkdownText";
import { useRecalls } from "@/hooks/useRecalls";
import { useAuth } from "@/hooks/useAuth";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import type { CaptureResponse, ChatAction, ChatResponse, ReminderResponse } from "@/types/api";
import { makeId } from "@/utils/id";
import { scheduleOrUpdateLocalReminder } from "@/utils/notifications";


type UserMessage = { id: string; role: "user"; text: string };

type AssistantTextMessage = { id: string; role: "assistant"; kind: "text"; text: string };
type AssistantCaptureMessage = {
  id: string;
  role: "assistant";
  kind: "capture";
  text: string;
  data: CaptureResponse;
};
type AssistantAnswerMessage = {
  id: string;
  role: "assistant";
  kind: "answer";
  text: string;
  data: ChatResponse;
};
type AssistantErrorMessage = {
  id: string;
  role: "assistant";
  kind: "error";
  text: string;
  retryText?: string;
};

type ChatMessage =
  | UserMessage
  | AssistantTextMessage
  | AssistantCaptureMessage
  | AssistantAnswerMessage
  | AssistantErrorMessage;

type WorkMode = "chat" | "link" | "save" | "reminder";


function cleanSourceTitle(raw: string | null | undefined): string {
  if (!raw) return "Saved source";
  try {
    return decodeURIComponent(raw).replace(/%20/g, " ");
  } catch {
    return raw.replace(/%20/g, " ");
  }
}

const chatActions: ChatAction[] = [
  "acknowledge",
  "conversation",
  "capture",
  "answer",
  "audit",
  "forget",
  "reminder",
  "self",
  "recent",
];

function getCleanFirstName(fullName?: string | null): string {
  if (!fullName) return "there";
  const trimmed = fullName.trim();
  if (!trimmed) return "there";

  const firstWord = trimmed.split(/\s+/)[0];
  if (!firstWord) return "there";

  const cleanPart = firstWord.split(/[._@\d]+/)[0] || firstWord;
  return cleanPart.charAt(0).toUpperCase() + cleanPart.slice(1);
}

function openingMessage(name: string | null | undefined): AssistantTextMessage {
  const first = getCleanFirstName(name);
  return {
    id: "opening",
    role: "assistant",
    kind: "text",
    text: `Welcome back, ${first}. What has your attention today?`,
  };
}


export default function ChatScreen() {
  const { session, isLoading: authLoading } = useAuth();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const inputRef = useRef<TextInput>(null);
  const listRef = useRef<FlatList<ChatMessage>>(null);
  const shouldStickToBottomRef = useRef(true);
  const initialScrollDoneRef = useRef(false);

  const [messages, setMessages] = useState<ChatMessage[]>([openingMessage(session?.name)]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [working, setWorking] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [workMode, setWorkMode] = useState<WorkMode>("chat");

  const scrollToEnd = useCallback((animated = true) => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated }), 80);
  }, []);

  const handleListScroll = useCallback((event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { contentOffset, contentSize, layoutMeasurement } = event.nativeEvent;
    const distanceFromBottom = contentSize.height - (contentOffset.y + layoutMeasurement.height);
    shouldStickToBottomRef.current = distanceFromBottom < 96;
  }, []);

  const handleContentSizeChange = useCallback(() => {
    if (!initialScrollDoneRef.current || shouldStickToBottomRef.current) {
      scrollToEnd(initialScrollDoneRef.current);
      initialScrollDoneRef.current = true;
    }
  }, [scrollToEnd]);

  const loadConversation = useCallback(
    async ({ silent = false }: { silent?: boolean } = {}) => {
      if (!session) return;

      if (!silent) {
        setHistoryLoading(true);
      }
      setHistoryError(null);

      let lastError: unknown = null;
      for (let attempt = 0; attempt < 3; attempt += 1) {
        try {
          const conv = await getCurrentConversation();
          const loaded: ChatMessage[] = conv?.messages?.length
            ? conv.messages.map((m) => {
                if (m.role === "user") {
                  return { id: m.id, role: "user", text: m.content };
                }
                const meta = m.metadata_json || {};
                if (m.action === "capture" && meta.capture) {
                  return {
                    id: m.id,
                    role: "assistant",
                    kind: "capture",
                    text: m.content,
                    data: meta.capture as any,
                  };
                }
                if (
                  m.action === "reminder" ||
                  m.action === "answer" ||
                  m.action === "self" ||
                  meta.reminder ||
                  meta.evidence
                ) {
                  const dataObj: ChatResponse = {
                    action: (m.action as any) || "conversation",
                    message: m.content,
                    saved: false,
                    capture: (meta.capture as any) || null,
                    reminder: (meta.reminder as any) || null,
                    evidence: (meta.evidence as any) || [],
                    knowledge_gaps: (meta.knowledge_gaps as any) || [],
                    tensions: (meta.tensions as any) || [],
                    next_step: (meta.next_step as any) || null,
                    preference_updates: (meta.preference_updates as any) || [],
                    preferences: (meta.preferences as any) || null,
                  };
                  return {
                    id: m.id,
                    role: "assistant",
                    kind: "answer",
                    text: m.content,
                    data: dataObj,
                  };
                }
                return {
                  id: m.id,
                  role: "assistant",
                  kind: "text",
                  text: m.content,
                };
              })
            : [openingMessage(session.name)];

          shouldStickToBottomRef.current = true;
          initialScrollDoneRef.current = false;
          setMessages(loaded);
          scrollToEnd(false);
          setHistoryLoading(false);
          return;
        } catch (error) {
          lastError = error;
          if (attempt === 0) {
            await new Promise((resolve) => setTimeout(resolve, 800));
          } else if (attempt === 1) {
            await new Promise((resolve) => setTimeout(resolve, 1500));
          }
        }
      }

      setHistoryLoading(false);
      setHistoryError(
        lastError instanceof Error
          ? "I could not load your earlier messages yet."
          : "Your earlier messages did not load. Pull down to try again.",
      );
    },
    [scrollToEnd, session],
  );

  useEffect(() => {
    if (authLoading) return;
    if (!session) {
      setMessages([openingMessage(null)]);
      setHistoryLoading(false);
      setHistoryError(null);
      return;
    }

    void loadConversation();
  }, [authLoading, loadConversation, session]);


  const sendText = useCallback(
    async (input: string) => {
      const text = input.trim();
      if (!text || working) return;

      const userMsg: UserMessage = { id: makeId("msg"), role: "user", text };
      shouldStickToBottomRef.current = true;
      setMessages((current) => [...current, userMsg]);
      setDraft("");
      setWorkMode(inferWorkMode(text));
      setWorking(true);
      scrollToEnd();

      try {
        const history = messages
          .filter((message) => !(message.role === "assistant" && message.kind === "error"))
          .slice(-12)
          .map((message) => ({ role: message.role, content: message.text }));

        const raw = await sendChatMessage({ message: text, history });
        const action: ChatAction = chatActions.includes(raw.action) ? raw.action : "conversation";

        const assistantMsg: ChatMessage =
          action === "capture" && raw.capture
            ? {
                id: makeId("msg"),
                role: "assistant",
                kind: "capture",
                text: raw.message,
                data: raw.capture,
              }
            : action === "answer" ||
                action === "reminder" ||
                action === "forget" ||
                action === "self" ||
                Boolean(raw.reminder) ||
                (raw.preference_updates && raw.preference_updates.length > 0)
              ? {
                  id: makeId("msg"),
                  role: "assistant",
                  kind: "answer",
                  text: raw.message,
                  data: raw,
                }
              : {
                  id: makeId("msg"),
                  role: "assistant",
                  kind: "text",
                  text: raw.message,
                };

        if ((action === "reminder" || raw.reminder) && raw.reminder) {
          const rawDueAt = raw.reminder.due_at;
          const nowIso = new Date().toISOString();
          console.log("\n==========================================");
          console.log("🔔 [CHAT REMINDER CREATED DIAGNOSTICS]");
          console.log(`1. Backend raw due_at: ${rawDueAt}`);
          console.log(`2. Local device time:  ${nowIso}`);
          console.log(`3. Reminder ID:        ${raw.reminder.id}`);
          console.log(`4. Reminder Content:   ${raw.reminder.content}`);
          console.log("==========================================\n");

          scheduleOrUpdateLocalReminder({
            reminderId: raw.reminder.id,
            title: "Reminder due",
            body: raw.reminder.content,
            dueAt: rawDueAt,
          }).catch(() => null);
        }

        setMessages((current) => [...current, assistantMsg]);

      } catch (err) {
        setMessages((current) => [
          ...current,
          {
            id: makeId("msg"),
            role: "assistant",
            kind: "error",
            text:
              err instanceof Error
                ? err.message
                : "Crowscap could not complete that thought.",
            retryText: text,
          },
        ]);
      } finally {
        setWorking(false);
        if (shouldStickToBottomRef.current) {
          scrollToEnd();
        }
      }
    },
    [messages, scrollToEnd, working],
  );

  const retry = useCallback(
    async (text: string) => {
      if (!text.trim() || working) return;
      await sendText(text);
    },
    [sendText, working],
  );

  const [pendingFile, setPendingFile] = useState<DocumentPicker.DocumentPickerAsset | null>(null);

  const pickFile = useCallback(async () => {
    if (working || uploadingFile) return;

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*", "text/*"],
        copyToCacheDirectory: true,
        multiple: false,
      });

      if (result.canceled || !result.assets?.[0]) return;
      setPendingFile(result.assets[0]);
    } catch {}
  }, [uploadingFile, working]);

  const handleSend = useCallback(async () => {
    if (pendingFile) {
      const fileToUpload = pendingFile;
      const note = draft.trim();
      setPendingFile(null);
      setDraft("");

      const userMsgText = note
        ? `${note}\n\nUploaded PDF: ${fileToUpload.name}`
        : `Uploaded PDF: ${fileToUpload.name}`;

      const userMsg: UserMessage = {
        id: makeId("msg"),
        role: "user",
        text: userMsgText,
      };
      shouldStickToBottomRef.current = true;
      setMessages((current) => [...current, userMsg]);
      setWorkMode("save");
      setUploadingFile(true);
      scrollToEnd();

      try {
        const capture = await capturePdf({
          uri: fileToUpload.uri,
          name: fileToUpload.name || "uploaded.pdf",
          mimeType: fileToUpload.mimeType || "application/pdf",
        });

        setMessages((current) => [
          ...current,
          {
            id: makeId("msg"),
            role: "assistant",
            kind: "capture",
            text: `I kept this PDF as ${
              capture.memories.length === 1
                ? "1 memory"
                : `${capture.memories.length} memories`
            }.`,
            data: capture,
          },
        ]);
      } catch (err) {
        setMessages((current) => [
          ...current,
          {
            id: makeId("msg"),
            role: "assistant",
            kind: "error",
            text:
              err instanceof Error
                ? err.message
                : "Crowscap could not upload that PDF.",
          },
        ]);
      } finally {
        setUploadingFile(false);
        if (shouldStickToBottomRef.current) {
          scrollToEnd();
        }
      }
    } else if (draft.trim()) {
      const textToSend = draft;
      setDraft("");
      await sendText(textToSend);
    }
  }, [draft, pendingFile, sendText, scrollToEnd]);


  const { data: recallData } = useRecalls();
  const hasUnreadRecalls = (recallData?.memories?.length ?? 0) > 0;

  const renderItem: ListRenderItem<ChatMessage> = useCallback(
    ({ item }) => <ChatTurn message={item} onRetry={retry} retryDisabled={working} />,
    [retry, working],
  );

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >

      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerLeft}>
          <BrandMark size={38} imageSize={29} />
          <View>
            <Text style={styles.headerTitle}>New thought</Text>
            <View style={styles.headerStatusRow}>
              <Text style={styles.headerSub}>Crowscap is listening</Text>
            </View>

          </View>
        </View>
        <View style={styles.headerRight}>
          <Pressable
            style={styles.headerIconButton}
            onPress={() => router.push("/(tabs)/recall" as never)}
            hitSlop={8}
          >
            <Icons.Bell size={19} color={tokens.colors.text} />
            {hasUnreadRecalls ? <View style={styles.bellDot} /> : null}
          </Pressable>
          <Pressable
            style={styles.headerIconButton}
            onPress={() => router.push("/settings" as never)}
            hitSlop={8}
          >
            <Icons.Settings size={19} color={tokens.colors.text} />
          </Pressable>
        </View>
      </View>



      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshing={historyLoading}
        onRefresh={() => void loadConversation()}
        showsVerticalScrollIndicator={false}
        keyboardDismissMode="interactive"
        keyboardShouldPersistTaps="handled"
        onScroll={handleListScroll}
        scrollEventThrottle={16}
        onContentSizeChange={handleContentSizeChange}
        ListHeaderComponent={historyError ? (
          <Pressable
            style={({ pressed }) => [styles.historyError, pressed && { opacity: 0.72 }]}
            onPress={() => void loadConversation()}
          >
            <Text style={styles.historyErrorText}>{historyError}</Text>
            <Text style={styles.historyErrorAction}>Tap to retry</Text>
          </Pressable>
        ) : null}
        ListFooterComponent={working || uploadingFile ? <ThinkingTurn mode={workMode} /> : null}
      />

      <Composer
        draft={draft}
        setDraft={setDraft}
        pendingFile={pendingFile}
        onRemoveFile={() => setPendingFile(null)}
        onSend={handleSend}
        onAttach={pickFile}
        working={working || uploadingFile}
        inputRef={inputRef}
        bottomInset={insets.bottom}
      />

    </KeyboardAvoidingView>
  );
}

function ChatTurn({
  message,
  onRetry,
  retryDisabled,
}: {
  message: ChatMessage;
  onRetry: (text: string) => void;
  retryDisabled: boolean;
}) {
  if (message.role === "user") {
    return (
      <View style={styles.userTurnRow}>
        <UserBubble text={message.text} />
      </View>
    );
  }

  return (
    <View style={styles.assistantTurnRow}>
      <BrandMark size={32} imageSize={24} />
      <View style={styles.assistantContent}>
        <MarkdownText text={message.text} />

        {message.kind === "capture" ? <CaptureReceipt data={message.data} /> : null}
        {message.kind === "answer" ? <AnswerFooter data={message.data} /> : null}

        {message.kind === "error" ? (
          <Pressable
            style={({ pressed }) => [styles.retryButton, pressed && { opacity: 0.65 }]}
            onPress={() => onRetry(message.retryText ?? message.text)}
            disabled={retryDisabled}
          >
            <Icons.Loader2 size={12} color="#7b7e82" />
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

function UserBubble({ text }: { text: string }) {
  // Split text into segments: URL vs plain text
  const URL_REGEX = /(https?:\/\/[^\s]+|www\.[^\s]+)/g;
  const segments: Array<{ type: "text" | "url"; value: string }> = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = URL_REGEX.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    segments.push({ type: "url", value: match[0] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    segments.push({ type: "text", value: text.slice(lastIndex) });
  }

  const hasUrl = segments.some((s) => s.type === "url");

  return (
    <View style={styles.userBubble}>
      {segments.length === 1 && !hasUrl ? (
        <Text style={styles.userBubbleText}>{text}</Text>
      ) : (
        <Text style={styles.userBubbleText}>
          {segments.map((seg, i) =>
            seg.type === "url" ? (
              <Text
                key={i}
                style={styles.userBubbleLink}
                onPress={() => Linking.openURL(seg.value.startsWith("http") ? seg.value : `https://${seg.value}`)}
              >
                {seg.value}
              </Text>
            ) : (
              <Text key={i}>{seg.value}</Text>
            )
          )}
        </Text>
      )}
    </View>
  );
}

function CaptureReceipt({ data }: { data: CaptureResponse }) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<"memories" | "original">("memories");
  const router = useRouter();
  const memCount = data.memories.length;
  const intents = data.inferred_intents.slice(0, 3);

  return (
    <View style={styles.receiptCard}>
      <Pressable
        style={styles.receiptHeaderRow}
        onPress={() => setExpanded((v) => !v)}
      >
        <View style={styles.receiptCheckCircle}>
          <Icons.Check size={14} color="#2d7058" />
        </View>
        <View style={styles.receiptCopy}>
          <Text style={styles.receiptLabel}>Memory receipt</Text>
          <Text style={styles.receiptMeta}>
            {memCount} {memCount === 1 ? "memory" : "memories"}
            {intents.length > 0 ? ` · ${intents.join(", ")}` : ""}
          </Text>
        </View>
        {expanded ? (
          <Icons.ChevronDown size={18} color="#787c80" />
        ) : (
          <Icons.ChevronRight size={18} color="#787c80" />
        )}
      </Pressable>

      {expanded ? (
        <>
          <View style={styles.receiptDividerLine} />
          <View style={styles.receiptAccordionContent}>
            {/* Tab Switcher: Memories | Original */}
            <View style={styles.receiptTabRow}>
              <Pressable
                style={[
                  styles.receiptTabBtn,
                  activeTab === "memories" && styles.receiptTabBtnActive,
                ]}
                onPress={() => setActiveTab("memories")}
              >
                <Text
                  style={[
                    styles.receiptTabText,
                    activeTab === "memories" && styles.receiptTabTextActive,
                  ]}
                >
                  Memories
                </Text>
              </Pressable>
              <Pressable
                style={[
                  styles.receiptTabBtn,
                  activeTab === "original" && styles.receiptTabBtnActive,
                ]}
                onPress={() => setActiveTab("original")}
              >
                <Icons.FileText
                  size={13}
                  color={activeTab === "original" ? "#111111" : "#5a5e62"}
                />
                <Text
                  style={[
                    styles.receiptTabText,
                    activeTab === "original" && styles.receiptTabTextActive,
                  ]}
                >
                  Original
                </Text>
              </Pressable>
            </View>

            {activeTab === "memories" ? (
              <View style={styles.receiptMemoryList}>
                {data.memories.map((mem) => (
                  <Pressable
                    key={mem.id}
                    style={styles.receiptMemoryCard}
                    onPress={() => router.push(
                      (`/(modals)/memory/${mem.id}?source_id=${data.source_id}`) as never
                    )}
                  >
                    <View style={styles.receiptMemoryCardTop}>
                      <View style={styles.receiptMemoryIconWrap}>
                        <Icons.Lightbulb size={15} color="#356b8f" />
                      </View>
                      <View style={styles.receiptMemoryCardMeta}>
                        <Text style={styles.receiptMemoryTypeLabel}>
                          {mem.memory_type}
                        </Text>
                        <Text style={styles.receiptMemoryDot}>·</Text>
                        <Text style={styles.receiptMemoryConfidence}>
                          {mem.confidence ? `${mem.confidence} confidence` : "high confidence"}
                        </Text>
                      </View>
                      <View style={styles.receiptSourceTag}>
                        <Text style={styles.receiptSourceTagText}>PDF</Text>
                      </View>
                    </View>

                    <Text style={styles.receiptMemoryBodyText}>
                      {mem.content || mem.summary}
                    </Text>
                  </Pressable>
                ))}
              </View>
            ) : (
            <View style={styles.receiptOriginalWrap}>
              <Text style={styles.receiptOriginalEyebrow}>EXACTLY AS SAVED</Text>
              {data.source_title ? (
                <Text style={styles.receiptOriginalTitle}>
                  {cleanSourceTitle(data.source_title)}
                </Text>
              ) : null}
              <ScrollView
                nestedScrollEnabled
                style={styles.receiptOriginalScroll}
                showsVerticalScrollIndicator={true}
              >
                <Text style={styles.receiptOriginalContent}>
                  {data.original_content || "No original content preview available."}
                </Text>
              </ScrollView>
            </View>

          )}
          </View>
        </>
      ) : null}
    </View>
  );

}



function extractReminderContent(text?: string): string | null {
  if (!text) return null;
  const match = text.match(/scheduled the reminder (?:for|to|about)?\s*["']?([^"'\n\.]+)["']?/i);
  return match ? match[1].trim() : null;
}

function formatReminderDueTime(dueAtIso?: string): string {
  if (!dueAtIso) return "Due soon";
  const date = new Date(dueAtIso);
  if (Number.isNaN(date.getTime())) return "Due soon";

  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");
  const timeStr = `${hours}:${minutes}`;

  if (isToday) {
    return `Due today at ${timeStr}`;
  }
  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const dateStr = `${monthNames[date.getMonth()]} ${date.getDate()}`;
  return `Due ${dateStr} at ${timeStr}`;
}

function ReminderCard({ reminder, fallbackText }: { reminder?: ReminderResponse | null; fallbackText?: string }) {
  const content = reminder?.content || extractReminderContent(fallbackText) || "Reminder";
  const dueAt = reminder?.due_at;
  const saveAsMemory = reminder?.save_as_memory ?? false;

  return (
    <View style={styles.reminderCard}>
      <View style={styles.reminderCardHeader}>
        <Icons.Clock3 size={15} color="#2d7058" />
        <Text style={styles.reminderCardEyebrow}>REMINDER SCHEDULED</Text>
      </View>

      <Text style={styles.reminderCardBody}>{content}</Text>

      <Text style={styles.reminderCardMeta}>
        {formatReminderDueTime(dueAt)} - {saveAsMemory ? "saved to memory" : "not saved to memory"}
      </Text>
    </View>
  );
}

function AnswerFooter({ data }: { data: ChatResponse }) {
  const isReminder = data.action === "reminder" || Boolean(data.reminder);
  if (!data.preference_updates?.length && !data.evidence?.length && !data.next_step && !isReminder) return null;

  return (
    <View style={styles.answerFooter}>
      {isReminder ? (
        <ReminderCard reminder={data.reminder} fallbackText={data.message} />
      ) : null}
      {data.preference_updates?.length ? (
        <InsightBlock label="Preference learned" items={data.preference_updates} tone="green" />
      ) : null}
      {data.next_step ? (
        <View style={styles.nextStep}>
          <Text style={styles.nextStepLabel}>Useful next move</Text>
          <MarkdownText text={data.next_step} compact />
        </View>
      ) : null}
      {data.evidence?.length ? (
        <View style={styles.evidenceToggle}>
          <Text style={styles.evidenceToggleText}>
            {data.evidence.length} memories informed this answer
          </Text>
          <Icons.ChevronRight size={16} color={tokens.colors.text} />
        </View>
      ) : null}
    </View>
  );
}


function InsightBlock({
  label,
  items,
  tone,
}: {
  label: string;
  items: string[];
  tone: "green" | "amber" | "rose";
}) {
  const toneStyle = tone === "green" ? styles.insightGreen : tone === "amber" ? styles.insightAmber : styles.insightRose;
  return (
    <View style={[styles.insightBlock, toneStyle]}>
      <Text style={styles.insightLabel}>{label}</Text>
      {items.slice(0, 4).map((item) => (
        <MarkdownText key={item} text={item} compact />
      ))}
    </View>
  );
}

function Composer({
  draft,
  setDraft,
  pendingFile,
  onRemoveFile,
  onSend,
  onAttach,
  working,
  inputRef,
  bottomInset,
}: {
  draft: string;
  setDraft: (value: string) => void;
  pendingFile: DocumentPicker.DocumentPickerAsset | null;
  onRemoveFile: () => void;
  onSend: () => void;
  onAttach: () => void;
  working: boolean;
  inputRef: RefObject<TextInput | null>;
  bottomInset: number;
}) {
  const canSend = (draft.trim().length > 0 || pendingFile !== null) && !working;

  return (
    <View style={[styles.composerWrap, { paddingBottom: 4 }]}>

      {pendingFile ? (
        <View style={styles.attachedPillRow}>
          <View style={styles.attachedPill}>
            <Icons.FileText size={15} color="#4f5356" />
            <Text style={styles.attachedPillName} numberOfLines={1}>
              {pendingFile.name}
            </Text>
            <Pressable onPress={onRemoveFile} hitSlop={8}>
              <Icons.X size={14} color="#777b7e" />
            </Pressable>
          </View>
        </View>
      ) : null}

      <View style={styles.composer}>
        <Pressable
          style={({ pressed }) => [styles.composerAction, pressed && { opacity: 0.65 }]}
          onPress={onAttach}
          hitSlop={6}
        >
          <Icons.Paperclip size={20} color="#65696f" />
        </Pressable>
        <TextInput
          ref={inputRef}
          style={styles.composerInput}
          value={draft}
          onChangeText={setDraft}
          placeholder="Save a thought, ask your memory..."
          placeholderTextColor="#8a8e94"
          multiline
          maxLength={40_000}
          returnKeyType="default"
          scrollEnabled
          textAlignVertical="center"
        />
        <Pressable
          style={({ pressed }) => [
            styles.sendButton,
            canSend && styles.sendButtonActive,
            pressed && canSend && { opacity: 0.8 },
          ]}
          onPress={onSend}
          disabled={!canSend}
          hitSlop={4}
        >
          <Icons.ArrowUp size={18} color={canSend ? "#ffffff" : "#a8acb1"} />
        </Pressable>
      </View>
    </View>
  );
}


function inferWorkMode(text: string): WorkMode {
  if (/\b(remind|reminder|tomorrow|today|tonight|morning|evening|hour|minute)\b/i.test(text)) {
    return "reminder";
  }
  if (/https?:\/\/|www\./i.test(text)) return "link";
  if (/\b(save|saving|remember|keep|archive|delete|forget)\b/i.test(text)) return "save";
  return "chat";
}

function ThinkingTurn({ mode }: { mode: WorkMode }) {
  const status: Record<WorkMode, { label: string; detail: string }> = {
    chat: {
      label: "Thinking",
      detail: "Checking nearby context before replying.",
    },
    link: {
      label: "Saving link",
      detail: "Keeping the reference first, then reading what is available.",
    },
    save: {
      label: "Saving memory",
      detail: "Finding the signal and keeping it clean.",
    },
    reminder: {
      label: "Setting reminder",
      detail: "Turning the request into a timely nudge.",
    },
  };
  const current = status[mode];

  return (
    <View style={styles.thinkingRow}>
      <BrandMark size={32} imageSize={24} />
      <View style={styles.thinkingContent}>
        <View style={styles.thinkingTop}>
          <Text style={styles.thinkingLabel}>{current.label}</Text>
          <ActivityIndicator size="small" color="#777b7e" />
        </View>
        <Text style={styles.thinkingText}>{current.detail}</Text>
        <View style={styles.progressTrack}>
          <View style={styles.progressFill} />
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
  headerRight: {
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

  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[3],
  },
  headerTitle: {
    fontSize: 16,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
    letterSpacing: 0,
  },
  headerStatusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 1,
  },
  statusDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: "#0f5132",
  },
  headerSub: {
    fontSize: 11,
    fontFamily: fontFamily.semibold,
    color: "#787c80",
  },
  headerIconButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  list: {
    paddingHorizontal: tokens.spacing[4],
    paddingTop: tokens.spacing[6],
    paddingBottom: 26,
    gap: tokens.spacing[7],
  },
  historyError: {
    borderWidth: 1,
    borderColor: "#ead8b6",
    backgroundColor: "#fff9ed",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  historyErrorText: {
    fontSize: 12,
    lineHeight: 18,
    fontFamily: fontFamily.semibold,
    color: "#6f5120",
  },
  historyErrorAction: {
    marginTop: 4,
    fontSize: 11,
    fontFamily: fontFamily.bold,
    color: "#9a6a12",
  },
  userTurnRow: {
    alignItems: "flex-end",
  },
  userBubble: {
    maxWidth: "86%",
    backgroundColor: "#f0f1f2",
    borderWidth: 1,
    borderColor: "#e8eaeb",
    borderRadius: 18,
    borderBottomRightRadius: 5,
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
  },
  userBubbleText: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#17191a",
    lineHeight: 20,
  },
  userBubbleLink: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#1a6ebd",
    lineHeight: 20,
    textDecorationLine: "underline",
  },
  assistantTurnRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: tokens.spacing[3],
  },
  assistantContent: {
    flex: 1,
    gap: tokens.spacing[3],
  },
  retryButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  retryText: {
    fontSize: 11,
    fontFamily: fontFamily.bold,
    color: "#7b7e82",
  },
  receiptCard: {
    borderWidth: 1,
    borderColor: "#e4ece6",
    backgroundColor: "#f7faf8",
    borderRadius: 8,
    overflow: "hidden",
  },
  receiptHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  receiptCheckCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#e8f3ed",
    alignItems: "center",
    justifyContent: "center",
  },
  receiptCopy: {
    flex: 1,
  },
  receiptLabel: {
    fontSize: 12.5,
    fontFamily: fontFamily.extrabold,
    color: "#25282b",
  },
  receiptMeta: {
    marginTop: 2,
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: "#787c80",
  },
  receiptDividerLine: {
    height: 1,
    backgroundColor: "#e4ece6",
    width: "100%",
  },
  receiptAccordionContent: {
    paddingHorizontal: 14,
    paddingTop: 12,
    paddingBottom: 14,
  },
  receiptTabRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#f0f2f4",
    borderRadius: 8,
    padding: 3,
    marginBottom: 12,
    gap: 4,
  },
  receiptTabBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 6,
    borderRadius: 6,
    gap: 6,
  },
  receiptTabBtnActive: {
    backgroundColor: "#ffffff",
    shadowColor: "#000000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  receiptTabText: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#5a5e62",
  },
  receiptTabTextActive: {
    color: "#111418",
    fontFamily: fontFamily.bold,
  },
  receiptMemoryList: {
    gap: 10,
  },
  receiptMemoryCard: {
    borderWidth: 1,
    borderColor: "#e3e5e8",
    backgroundColor: "#ffffff",
    borderRadius: 8,
    padding: 14,
    gap: 10,
  },
  receiptMemoryCardTop: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  receiptMemoryIconWrap: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: "#e8f1f5",
    alignItems: "center",
    justifyContent: "center",
  },
  receiptMemoryCardMeta: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  receiptMemoryTypeLabel: {
    fontSize: 10.5,
    fontFamily: fontFamily.extrabold,
    color: "#55595d",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  receiptMemoryDot: {
    fontSize: 11,
    color: "#b0b4b8",
  },

  receiptMemoryConfidence: {
    fontSize: 11,
    fontFamily: fontFamily.medium,
    color: "#8a8e94",
  },
  receiptSourceTag: {
    backgroundColor: "#ededee",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  receiptSourceTagText: {
    fontSize: 10,
    fontFamily: fontFamily.bold,
    color: "#66696c",
  },
  receiptMemoryBodyText: {
    fontSize: 13.5,
    lineHeight: 21,
    fontFamily: fontFamily.medium,
    color: "#1c1e20",
  },
  receiptOriginalWrap: {
    padding: 14,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#e3e5e8",
    borderRadius: 8,
    gap: 8,
  },
  receiptOriginalEyebrow: {
    fontSize: 10.5,
    fontFamily: fontFamily.extrabold,
    color: "#787c80",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  receiptOriginalTitle: {
    fontSize: 14,
    lineHeight: 19,
    fontFamily: fontFamily.bold,
    color: "#111418",
  },
  receiptOriginalScroll: {
    maxHeight: 260,
  },
  receiptOriginalContent: {

    fontSize: 13.5,
    lineHeight: 20,
    fontFamily: fontFamily.medium,
    color: "#202224",
  },



  reminderCard: {
    backgroundColor: "#edf6f1",
    borderWidth: 1,
    borderColor: "#d2e8dc",
    borderRadius: 12,
    padding: 14,
    marginTop: 6,
    gap: 6,
  },
  reminderCardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  reminderCardEyebrow: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#2d7058",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  reminderCardBody: {
    fontSize: 14,
    fontFamily: fontFamily.medium,
    color: "#1c1e20",
  },
  reminderCardMeta: {
    fontSize: 12,
    fontFamily: fontFamily.medium,
    color: "#5f7e6e",
  },

  answerFooter: {
    gap: tokens.spacing[3],
  },

  insightBlock: {
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    gap: 8,
  },
  insightGreen: {
    borderColor: "#d7e5dc",
    backgroundColor: "#f1f7f4",
  },
  insightAmber: {
    borderColor: "#eadbbd",
    backgroundColor: "#fcf6ea",
  },
  insightRose: {
    borderColor: "#ead3d5",
    backgroundColor: "#fbf1f2",
  },
  insightLabel: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#4d5154",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  nextStep: {
    borderWidth: 1,
    borderColor: "#d7e5dc",
    backgroundColor: "#f1f7f4",
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    gap: 8,
  },
  nextStepLabel: {
    fontSize: 11,
    fontFamily: fontFamily.extrabold,
    color: "#2d7058",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },

  evidenceToggle: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: "#e0e2e3",
    borderRadius: 10,
    paddingHorizontal: tokens.spacing[4],
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  evidenceToggleText: {
    fontSize: 12,
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  thinkingRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: tokens.spacing[3],
  },
  thinkingContent: {
    flex: 1,
    paddingTop: 2,
  },
  thinkingTop: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  thinkingLabel: {
    fontSize: 12,
    fontFamily: fontFamily.extrabold,
    color: "#202223",
  },
  thinkingText: {
    marginTop: 2,
    fontSize: 11,
    lineHeight: 16,
    fontFamily: fontFamily.medium,
    color: "#73777a",
  },
  progressTrack: {
    marginTop: 9,
    width: 168,
    height: 2,
    backgroundColor: "#e1e3e4",
    overflow: "hidden",
  },
  progressFill: {
    width: "55%",
    height: "100%",
    backgroundColor: tokens.colors.text,
  },
  composerWrap: {
    backgroundColor: "#ffffff",
    borderTopWidth: 1,
    borderTopColor: "#f0f1f3",
    paddingHorizontal: 12,
    paddingTop: 4,
  },

  attachedPillRow: {
    flexDirection: "row",
    marginBottom: 8,
  },
  attachedPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#f0f2f4",
    borderWidth: 1,
    borderColor: "#e1e3e7",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 6,
    maxWidth: "85%",
  },
  attachedPillName: {
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#303437",
    maxWidth: 180,
  },

  composer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#ffffff",
    borderRadius: 28,
    borderWidth: 1,
    borderColor: "#e3e5e8",
    paddingHorizontal: 12,
    paddingVertical: 4,
    minHeight: 52,
  },


  composerAction: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
  },
  composerInput: {
    flex: 1,
    fontSize: 14.5,
    fontFamily: fontFamily.regular,
    color: "#000",
    lineHeight: 20,
    maxHeight: 120,
    paddingHorizontal: 4,
    paddingVertical: Platform.OS === "ios" ? 8 : 0,
  },
  sendButton: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "#d5d8dc",
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonActive: {
    backgroundColor: tokens.colors.text,
  },
});
