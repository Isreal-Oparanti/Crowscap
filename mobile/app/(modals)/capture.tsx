import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ScrollView,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useState } from "react";
import { captureText } from "@/api/captures";
import type { CaptureResponse } from "@/types/api";
import { validateCaptureText } from "@/utils/validation";
import { tokens } from "@/theme/tokens";

const INTENTS = [
  { key: "learned", label: "Learned" },
  { key: "remember", label: "Remember" },
  { key: "apply", label: "Apply" },
  { key: "verify", label: "Verify" },
  { key: "reference", label: "Reference" },
  { key: "watch_later", label: "Watch later" },
  { key: "read_later", label: "Read later" },
  { key: "inspiration", label: "Inspiration" },
  { key: "disagree", label: "Disagree" },
  { key: "question", label: "Question" },
] as const;

export default function CaptureModal() {
  const router = useRouter();
  const params = useLocalSearchParams<{ initialContent?: string }>();
  const insets = useSafeAreaInsets();
  const [text, setText] = useState(params.initialContent ?? "");
  const [note, setNote] = useState("");
  const [selectedIntent, setSelectedIntent] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  async function handleCapture() {
    const validationError = validateCaptureText(text);
    if (validationError) {
      Alert.alert("Cannot capture", validationError);
      return;
    }

    setWorking(true);
    try {
      const result: CaptureResponse = await captureText({
        content: text,
        intent_text: selectedIntent ?? undefined,
        user_note: note.trim() || undefined,
      });

      // Navigate to result screen with the capture data
      router.replace({
        pathname: "/(modals)/capture-result",
        params: { data: JSON.stringify(result) },
      });
    } catch (err) {
      setWorking(false);
      Alert.alert(
        "Capture failed",
        err instanceof Error ? err.message : "Could not save that memory. Try again."
      );
    }
  }

  const canCapture = text.trim().length >= 10 && !working;

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      {/* Handle bar */}
      <View style={styles.handleBar} />

      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top > 0 ? 0 : 8 }]}>
        <View>
          <Text style={styles.headerTitle}>Capture</Text>
          <Text style={styles.headerSub}>Save a learning fragment</Text>
        </View>
        <Pressable
          style={styles.closeButton}
          onPress={() => router.back()}
          hitSlop={8}
        >
          <Feather name="x" size={18} color={tokens.colors.textMuted} />
        </Pressable>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: insets.bottom + 24 },
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* Main text input */}
        <View style={styles.section}>
          <Text style={styles.label}>CONTENT</Text>
          <TextInput
            style={styles.contentInput}
            value={text}
            onChangeText={setText}
            placeholder={"Paste a link, note, quote, video URL, or idea…"}
            placeholderTextColor="#b4b7b9"
            multiline
            autoFocus
            maxLength={40_000}
            textAlignVertical="top"
          />
          <Text style={styles.charCount}>
            {text.length.toLocaleString()} / 40,000
          </Text>
        </View>

        {/* Intent picker */}
        <View style={styles.section}>
          <Text style={styles.label}>WHY ARE YOU SAVING THIS?</Text>
          <Text style={styles.intentHint}>
            Optional — Crowscap will infer intent if you skip this.
          </Text>
          <View style={styles.intentGrid}>
            {INTENTS.map((intent) => {
              const active = selectedIntent === intent.key;
              return (
                <Pressable
                  key={intent.key}
                  style={({ pressed }) => [
                    styles.intentPill,
                    active && styles.intentPillActive,
                    pressed && !active && styles.intentPillPressed,
                  ]}
                  onPress={() =>
                    setSelectedIntent(active ? null : intent.key)
                  }
                >
                  <Text
                    style={[
                      styles.intentPillText,
                      active && styles.intentPillTextActive,
                    ]}
                  >
                    {intent.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        {/* Note */}
        <View style={styles.section}>
          <Text style={styles.label}>NOTE (optional)</Text>
          <TextInput
            style={styles.noteInput}
            value={note}
            onChangeText={setNote}
            placeholder="Add context for yourself…"
            placeholderTextColor="#b4b7b9"
            multiline
            maxLength={1_000}
            textAlignVertical="top"
          />
        </View>

        {/* Save button */}
        <Pressable
          style={({ pressed }) => [
            styles.saveButton,
            !canCapture && styles.saveButtonDisabled,
            pressed && canCapture && { opacity: 0.85 },
          ]}
          onPress={handleCapture}
          disabled={!canCapture}
        >
          {working ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <>
              <Feather name="zap" size={15} color="#ffffff" />
              <Text style={styles.saveButtonText}>Save to memory</Text>
            </>
          )}
        </Pressable>

        {/* Info note */}
        <View style={styles.infoRow}>
          <Feather name="lock" size={11} color="#9a9d9f" />
          <Text style={styles.infoText}>
            Crowscap extracts structured memories from this content and stores them privately.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#ffffff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    overflow: "hidden",
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
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e7e8e9",
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: tokens.colors.text,
    letterSpacing: -0.3,
  },
  headerSub: {
    fontSize: 11,
    fontWeight: "500",
    color: tokens.colors.textMuted,
    marginTop: 2,
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#f1f2f3",
    alignItems: "center",
    justifyContent: "center",
  },

  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: tokens.spacing[5],
    paddingTop: tokens.spacing[5],
    gap: tokens.spacing[6],
  },

  section: {
    gap: tokens.spacing[2],
  },
  label: {
    fontSize: 10,
    fontWeight: "800",
    color: "#8a8d90",
    letterSpacing: 0.6,
  },

  contentInput: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: 12,
    padding: tokens.spacing[4],
    fontSize: 14,
    fontWeight: "400",
    color: tokens.colors.text,
    lineHeight: 22,
    minHeight: 140,
    backgroundColor: "#fafafa",
    textAlignVertical: "top",
  },
  charCount: {
    fontSize: 10,
    fontWeight: "500",
    color: "#b4b7b9",
    alignSelf: "flex-end",
  },

  intentHint: {
    fontSize: 11,
    fontWeight: "400",
    color: "#9a9d9f",
    marginBottom: 4,
  },
  intentGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  intentPill: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: tokens.radius.full,
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: "#ffffff",
  },
  intentPillActive: {
    backgroundColor: tokens.colors.text,
    borderColor: tokens.colors.text,
  },
  intentPillPressed: {
    backgroundColor: "#f1f2f3",
  },
  intentPillText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#4d5154",
  },
  intentPillTextActive: {
    color: "#ffffff",
  },

  noteInput: {
    borderWidth: 1,
    borderColor: "#e1e3e4",
    borderRadius: 12,
    padding: tokens.spacing[4],
    fontSize: 13,
    fontWeight: "400",
    color: tokens.colors.text,
    lineHeight: 20,
    minHeight: 72,
    backgroundColor: "#fafafa",
    textAlignVertical: "top",
  },

  saveButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 52,
    borderRadius: 12,
    backgroundColor: tokens.colors.text,
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.14,
    shadowRadius: 20,
    elevation: 4,
  },
  saveButtonDisabled: {
    backgroundColor: "#c4c7c9",
    shadowOpacity: 0,
    elevation: 0,
  },
  saveButtonText: {
    fontSize: 14,
    fontWeight: "800",
    color: "#ffffff",
    letterSpacing: -0.2,
  },

  infoRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
  },
  infoText: {
    fontSize: 11,
    fontWeight: "400",
    color: "#9a9d9f",
    lineHeight: 16,
    flex: 1,
  },
});
