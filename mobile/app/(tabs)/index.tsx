import {
  View,
  Text,
  TextInput,
  StyleSheet,
  FlatList,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useRef, useState, useCallback } from "react";
import { useRouter } from "expo-router";
import { useAuth } from "@/hooks/useAuth";
import { sendChatMessage } from "@/api/chat";
import { BrandMark } from "@/components/shell/BrandMark";
import type { ChatAction, ChatResponse, CaptureResponse } from "@/types/api";
import { tokens } from "@/theme/tokens";

// ─── Types ────────────────────────────────────────────────────────────────────

type UserMessage = { id: string; role: "user"; text: string };
type AssistantTextMessage = { id: string; role: "assistant"; kind: "text"; text: string };
type AssistantCaptureMessage = { id: string; role: "assistant"; kind: "capture"; text: string; data: CaptureResponse };
type AssistantAnswerMessage = { id: string; role: "assistant"; kind: "answer"; text: string; data: ChatResponse };
type AssistantErrorMessage = { id: string; role: "assistant"; kind: "error"; text: string; retryText?: string };

type ChatMessage =
  | UserMessage
  | AssistantTextMessage
  | AssistantCaptureMessage
  | AssistantAnswerMessage
  | AssistantErrorMessage;

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CHAT_ACTIONS: ChatAction[] = [
  "acknowledge", "conversation", "capture", "answer",
  "audit", "forget", "reminder", "self", "recent",
];

function openingMessage(name: string | null | undefined): AssistantTextMessage {
  const first = name?.split(/\s+/)[0] ?? "there";
  return {
    id: "opening",
    role: "assistant",
    kind: "text",
    text: `Welcome back, ${first}. What has your attention today?`,
  };
}

// ─── Main Screen ──────────────────────────────────────────────────────────────

export default function ChatScreen() {
  const { session } = useAuth();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const inputRef = useRef<TextInput>(null);
  const listRef = useRef<FlatList>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([
    openingMessage(session?.name),
  ]);
  const [draft, setDraft] = useState("");
  const [working, setWorking] = useState(false);

  const scrollToEnd = useCallback(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);
  }, []);

  const sendText = useCallback(async (input: string) => {
    const text = input.trim();
    if (!text || working) return;

    const userMsg: UserMessage = { id: crypto.randomUUID(), role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setDraft("");
    setWorking(true);
    scrollToEnd();

    try {
      const history = messages
        .filter((m) => !(m.role === "assistant" && m.kind === "error"))
        .slice(-12)
        .map((m) => ({ role: m.role, content: m.text }));

      const raw = await sendChatMessage({ message: text, history });

      const action: ChatAction = CHAT_ACTIONS.includes(raw.action) ? raw.action : "conversation";

      let assistantMsg: ChatMessage;

      if (action === "capture" && raw.capture) {
        assistantMsg = {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "capture",
          text: raw.message,
          data: raw.capture,
        };
      } else if (
        action === "answer" ||
        action === "forget" ||
        action === "self" ||
        (raw.preference_updates && raw.preference_updates.length > 0)
      ) {
        assistantMsg = {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "answer",
          text: raw.message,
          data: raw,
        };
      } else {
        assistantMsg = {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "text",
          text: raw.message,
        };
      }

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "error",
          text: err instanceof Error ? err.message : "I could not complete that thought.",
          retryText: text,
        },
      ]);
    } finally {
      setWorking(false);
      scrollToEnd();
    }
  }, [messages, scrollToEnd, working]);

  async function send() {
    await sendText(draft);
  }

  const retry = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || working) return;
    await sendText(trimmed);
  }, [sendText, working]);

  const renderItem = useCallback(
    ({ item }: { item: ChatMessage }) => (
      <ChatTurn message={item} onRetry={retry} retryDisabled={working} />
    ),
    [retry, working]
  );

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={0}
    >
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerLeft}>
          <BrandMark size={36} imageSize={27} />
          <View>
            <Text style={styles.headerTitle}>New thought</Text>
            <View style={styles.headerStatusRow}>
              <View style={styles.statusDot} />
              <Text style={styles.headerSub}>Crowscap is listening</Text>
            </View>
          </View>
        </View>
        <Pressable
          style={styles.captureButton}
          onPress={() => router.push("/(modals)/capture")}
          hitSlop={8}
        >
          <Feather name="plus" size={16} color="#ffffff" />
          <Text style={styles.captureButtonText}>Capture</Text>
        </Pressable>
      </View>

      {/* Message list */}
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={[styles.list, { paddingBottom: 24 }]}
        showsVerticalScrollIndicator={false}
        onContentSizeChange={scrollToEnd}
        keyboardDismissMode="interactive"
        keyboardShouldPersistTaps="handled"
        ListFooterComponent={
          working ? (
            <View style={styles.thinkingRow}>
              <View style={styles.thinkingBubble}>
                <ActivityIndicator size="small" color="#777a7e" />
                <Text style={styles.thinkingText}>Thinking…</Text>
              </View>
            </View>
          ) : null
        }
      />

      {/* Composer */}
      <Composer
        draft={draft}
        setDraft={setDraft}
        onSend={send}
        working={working}
        inputRef={inputRef}
        bottomInset={insets.bottom}
      />
    </KeyboardAvoidingView>
  );
}

// ─── Chat Turn ────────────────────────────────────────────────────────────────

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
        <View style={styles.userBubble}>
          <Text style={styles.userBubbleText}>{message.text}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.assistantTurnRow}>
      <BrandMark size={32} imageSize={24} />

      <View style={styles.assistantContent}>
        <Text style={styles.assistantText}>{message.text}</Text>

        {/* Capture receipt */}
        {message.kind === "capture" && message.data && (
          <CaptureReceipt data={message.data} />
        )}

        {/* Answer — evidence pills */}
        {message.kind === "answer" && message.data && (
          <AnswerFooter data={message.data} />
        )}

        {/* Error */}
        {message.kind === "error" && (
          <Pressable
            style={({ pressed }) => [styles.retryButton, pressed && { opacity: 0.65 }]}
            onPress={() => onRetry(message.retryText ?? message.text)}
            disabled={retryDisabled}
          >
            <Feather name="refresh-cw" size={12} color="#7b7e82" />
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

// ─── Capture Receipt ──────────────────────────────────────────────────────────

function CaptureReceipt({ data }: { data: CaptureResponse }) {
  const memCount = data.memories.length;
  const intents = data.inferred_intents.slice(0, 3);

  return (
    <View style={styles.receiptCard}>
      <View style={styles.receiptHeader}>
        <View style={styles.receiptCheckCircle}>
          <Feather name="check" size={12} color="#245e4b" />
        </View>
        <Text style={styles.receiptLabel}>MEMORY SAVED</Text>
      </View>
      {data.source_title ? (
        <Text style={styles.receiptTitle}>{data.source_title}</Text>
      ) : null}
      <Text style={styles.receiptMeta}>
        {memCount} {memCount === 1 ? "memory" : "memories"} extracted
        {intents.length > 0 ? ` · ${intents.join(", ")}` : ""}
      </Text>
    </View>
  );
}

// ─── Answer Footer ────────────────────────────────────────────────────────────

function AnswerFooter({ data }: { data: ChatResponse }) {
  if (!data.evidence?.length && !data.next_step) return null;

  return (
    <View style={styles.answerFooter}>
      {data.evidence.slice(0, 3).map((ev, i) => (
        <View key={ev.memory_id ?? i} style={styles.evidencePill}>
          <Text style={styles.evidencePillText} numberOfLines={2}>
            {ev.content}
          </Text>
          <Text style={styles.evidenceSource}>{ev.source_title ?? "Memory"}</Text>
        </View>
      ))}
      {data.next_step ? (
        <View style={styles.nextStep}>
          <Feather name="arrow-right" size={11} color="#4d5154" />
          <Text style={styles.nextStepText}>{data.next_step}</Text>
        </View>
      ) : null}
    </View>
  );
}

// ─── Composer ─────────────────────────────────────────────────────────────────

function Composer({
  draft,
  setDraft,
  onSend,
  working,
  inputRef,
  bottomInset,
}: {
  draft: string;
  setDraft: (v: string) => void;
  onSend: () => void;
  working: boolean;
  inputRef: React.RefObject<TextInput | null>;
  bottomInset: number;
}) {
  const router = useRouter();
  const canSend = draft.trim().length > 0 && !working;

  return (
    <View style={[styles.composerWrap, { paddingBottom: bottomInset + 8 }]}>
      <View style={styles.composer}>
        {/* Attach / capture shortcut */}
        <Pressable
          style={styles.composerAction}
          onPress={() => router.push("/(modals)/capture")}
          hitSlop={8}
        >
          <Feather name="paperclip" size={18} color="#9a9d9f" />
        </Pressable>

        <TextInput
          ref={inputRef}
          style={styles.composerInput}
          value={draft}
          onChangeText={setDraft}
          placeholder="Share a thought, or ask your memory…"
          placeholderTextColor="#b4b7b9"
          multiline
          maxLength={40_000}
          returnKeyType="default"
          enablesReturnKeyAutomatically={false}
          scrollEnabled
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
          <Feather
            name="arrow-up"
            size={16}
            color={canSend ? "#ffffff" : "#c4c7c9"}
          />
        </Pressable>
      </View>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#ffffff",
  },

  // Header
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing[4],
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e7e8e9",
    backgroundColor: "#ffffff",
  },
  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[3],
  },
  brandMark: {
    width: 36,
    height: 36,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#e4e5e6",
    backgroundColor: "#ffffff",
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
    elevation: 2,
  },
  headerTitle: {
    fontSize: 14,
    fontWeight: "800",
    color: tokens.colors.text,
    letterSpacing: -0.2,
  },
  headerStatusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 1,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#0f5132",
  },
  headerSub: {
    fontSize: 10,
    fontWeight: "600",
    color: "#787c80",
  },
  captureButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: tokens.colors.text,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  captureButtonText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#ffffff",
  },

  // Message list
  list: {
    paddingHorizontal: tokens.spacing[4],
    paddingTop: tokens.spacing[6],
    gap: tokens.spacing[7],
  },

  // User bubble
  userTurnRow: {
    alignItems: "flex-end",
  },
  userBubble: {
    maxWidth: "82%",
    backgroundColor: "#eef0f1",
    borderRadius: 18,
    borderBottomRightRadius: 5,
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 2,
    elevation: 1,
  },
  userBubbleText: {
    fontSize: 13,
    fontWeight: "500",
    color: "#17191a",
    lineHeight: 20,
  },

  // Assistant
  assistantTurnRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: tokens.spacing[3],
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: "#e4e5e6",
    backgroundColor: "#ffffff",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
    flexShrink: 0,
  },
  assistantContent: {
    flex: 1,
    gap: tokens.spacing[3],
  },
  assistantText: {
    fontSize: 13,
    fontWeight: "500",
    color: "#252627",
    lineHeight: 22,
    flexShrink: 1,
  },

  // Thinking
  thinkingRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[4],
    marginTop: tokens.spacing[7],
  },
  thinkingBubble: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[2],
    borderWidth: 1,
    borderColor: "#e7e8e9",
    backgroundColor: "#fafafa",
    borderRadius: 10,
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[2],
  },
  thinkingText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#888b8e",
  },

  // Retry
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
    fontWeight: "600",
    color: "#7b7e82",
  },

  // Capture receipt
  receiptCard: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    backgroundColor: "#ffffff",
    borderRadius: 14,
    padding: tokens.spacing[4],
    gap: tokens.spacing[2],
  },
  receiptHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  receiptCheckCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: "#edf5f1",
    alignItems: "center",
    justifyContent: "center",
  },
  receiptLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: "#303437",
    letterSpacing: 0.5,
  },
  receiptTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: tokens.colors.text,
    lineHeight: 18,
  },
  receiptMeta: {
    fontSize: 11,
    fontWeight: "500",
    color: "#787c80",
  },

  // Answer footer
  answerFooter: {
    gap: tokens.spacing[2],
  },
  evidencePill: {
    borderWidth: 1,
    borderColor: "#e2e4e5",
    backgroundColor: "#fafafa",
    borderRadius: 10,
    padding: tokens.spacing[3],
    gap: 3,
  },
  evidencePillText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#3a3c3e",
    lineHeight: 17,
  },
  evidenceSource: {
    fontSize: 10,
    fontWeight: "600",
    color: "#9a9d9f",
  },
  nextStep: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    paddingTop: 2,
  },
  nextStepText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#4d5154",
    lineHeight: 17,
    flex: 1,
  },

  // Composer
  composerWrap: {
    backgroundColor: "#ffffff",
    borderTopWidth: 1,
    borderTopColor: "#e7e8e9",
    paddingHorizontal: tokens.spacing[4],
    paddingTop: tokens.spacing[3],
  },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: tokens.spacing[2],
    backgroundColor: "#f5f6f7",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#e2e4e5",
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[2],
    minHeight: 48,
  },
  composerAction: {
    padding: 4,
    marginBottom: 2,
  },
  composerInput: {
    flex: 1,
    fontSize: 14,
    fontWeight: "400",
    color: tokens.colors.text,
    lineHeight: 20,
    maxHeight: 160,
    paddingTop: Platform.OS === "ios" ? 4 : 0,
    paddingBottom: Platform.OS === "ios" ? 4 : 0,
  },
  sendButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#d0d2d4",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 2,
  },
  sendButtonActive: {
    backgroundColor: tokens.colors.text,
  },
});
