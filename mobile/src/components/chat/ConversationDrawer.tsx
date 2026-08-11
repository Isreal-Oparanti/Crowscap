import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { deleteConversation, listConversations } from "@/api/chat";
import { BrandMark } from "@/components/shell/BrandMark";
import { Icons } from "@/components/ui/Icon";
import { useAuth } from "@/hooks/useAuth";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";
import type { ConversationResponse } from "@/types/api";

type ConversationDrawerProps = {
  visible: boolean;
  onClose: () => void;
  currentConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
};

export function ConversationDrawer({
  visible,
  onClose,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}: ConversationDrawerProps) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { session } = useAuth();

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (visible) {
      void fetchConversations();
    }
  }, [visible]);

  async function fetchConversations() {
    setLoading(true);
    try {
      const data = await listConversations(50);
      setConversations(data);
    } catch {
      // Ignore background load error
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(conversationId: string, title: string) {
    Alert.alert(
      "Delete Conversation",
      `Are you sure you want to delete "${title || "this chat"}"?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            setDeletingId(conversationId);
            try {
              await deleteConversation(conversationId);
              setConversations((current) =>
                current.filter((item) => item.id !== conversationId)
              );
              if (currentConversationId === conversationId) {
                onNewConversation();
              }
            } catch {
              Alert.alert("Error", "Could not delete this conversation.");
            } finally {
              setDeletingId(null);
            }
          },
        },
      ]
    );
  }

  function formatTime(iso: string) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  }

  const userInitial = (session?.email?.[0] || session?.name?.[0] || "U").toUpperCase();

  return (
    <Modal
      visible={visible}
      animationType="fade"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Pressable style={styles.backdrop} onPress={onClose} />

        <View style={[styles.drawerContainer, { paddingTop: insets.top + 16, paddingBottom: Math.max(insets.bottom, 16) }]}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.brandRow}>
              <BrandMark size={32} imageSize={24} />
              <Text style={styles.brandTitle}>Crowscap</Text>
            </View>
            <Pressable style={styles.iconButton} onPress={onClose} hitSlop={8}>
              <Icons.X size={20} color={tokens.colors.text} />
            </Pressable>
          </View>

          {/* New Chat Button */}
          <Pressable
            style={({ pressed }) => [
              styles.newChatButton,
              pressed && styles.newChatButtonPressed,
            ]}
            onPress={() => {
              onNewConversation();
              onClose();
            }}
          >
            <Icons.Plus size={18} color="#FFFFFF" />
            <Text style={styles.newChatText}>New Conversation</Text>
          </Pressable>

          <Text style={styles.sectionLabel}>CHAT HISTORY</Text>

          {/* Conversations Scroll View */}
          <ScrollView
            style={styles.scrollList}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {loading && conversations.length === 0 ? (
              <View style={styles.loadingBox}>
                <ActivityIndicator size="small" color="#2d7058" />
                <Text style={styles.loadingText}>Loading chats...</Text>
              </View>
            ) : conversations.length === 0 ? (
              <Text style={styles.emptyText}>No previous conversations found.</Text>
            ) : (
              conversations.map((item) => {
                const isActive = item.id === currentConversationId;
                const isDeleting = item.id === deletingId;

                return (
                  <Pressable
                    key={item.id}
                    style={({ pressed }) => [
                      styles.convoRow,
                      isActive && styles.convoRowActive,
                      pressed && styles.convoRowPressed,
                    ]}
                    onPress={() => {
                      onSelectConversation(item.id);
                      onClose();
                    }}
                  >
                    <Icons.MessageCircle
                      size={17}
                      color={isActive ? "#2d7058" : tokens.colors.textMuted}
                    />
                    <View style={styles.convoTextCol}>
                      <Text
                        style={[
                          styles.convoTitle,
                          isActive && styles.convoTitleActive,
                        ]}
                        numberOfLines={1}
                      >
                        {item.title || "Untitled Conversation"}
                      </Text>
                      {item.updated_at ? (
                        <Text style={styles.convoTime}>
                          {formatTime(item.updated_at)}
                        </Text>
                      ) : null}
                    </View>

                    <Pressable
                      style={styles.deleteButton}
                      disabled={isDeleting}
                      onPress={(e) => {
                        e.stopPropagation();
                        void handleDelete(item.id, item.title);
                      }}
                      hitSlop={8}
                    >
                      {isDeleting ? (
                        <ActivityIndicator size="small" color={tokens.colors.danger} />
                      ) : (
                        <Icons.Trash2 size={15} color={tokens.colors.textMuted} />
                      )}
                    </Pressable>
                  </Pressable>
                );
              })
            )}
          </ScrollView>

          {/* Footer User Profile */}
          <View style={styles.footerProfile}>
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarText}>{userInitial}</Text>
            </View>
            <View style={styles.userInfo}>
              <Text style={styles.userName} numberOfLines={1}>
                {session?.name || "Crowscap User"}
              </Text>
              <Text style={styles.userEmail} numberOfLines={1}>
                {session?.email || ""}
              </Text>
            </View>
            <Pressable
              style={styles.settingsButton}
              onPress={() => {
                onClose();
                router.push("/settings" as never);
              }}
              hitSlop={8}
            >
              <Icons.Settings size={18} color={tokens.colors.text} />
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.45)",
    flexDirection: "row",
  },
  backdrop: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  },
  drawerContainer: {
    width: "82%",
    maxWidth: 320,
    backgroundColor: tokens.colors.surface,
    height: "100%",
    paddingHorizontal: 16,
    borderRightWidth: 1,
    borderRightColor: tokens.colors.border,
    shadowColor: "#000",
    shadowOffset: { width: 4, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 16,
    elevation: 20,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 20,
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  brandTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 18,
    color: tokens.colors.text,
  },
  iconButton: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: tokens.colors.surface,
  },
  newChatButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#2d7058",
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    marginBottom: 20,
  },
  newChatButtonPressed: {
    opacity: 0.85,
  },
  newChatText: {
    fontFamily: fontFamily.semibold,
    fontSize: 14,
    color: "#FFFFFF",
  },
  sectionLabel: {
    fontFamily: fontFamily.extrabold,
    fontSize: 10,
    letterSpacing: 1,
    color: tokens.colors.textMuted,
    marginBottom: 10,
  },
  scrollList: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 16,
    gap: 6,
  },
  loadingBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 16,
  },
  loadingText: {
    fontFamily: fontFamily.medium,
    fontSize: 12,
    color: tokens.colors.textMuted,
  },
  emptyText: {
    fontFamily: fontFamily.regular,
    fontSize: 13,
    color: tokens.colors.textMuted,
    paddingVertical: 12,
  },
  convoRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 11,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: "transparent",
    gap: 10,
  },
  convoRowActive: {
    backgroundColor: "#eaf3ee",
    borderWidth: 1,
    borderColor: tokens.colors.border,
  },
  convoRowPressed: {
    backgroundColor: "#f5f6f7",
  },
  convoTextCol: {
    flex: 1,
  },
  convoTitle: {
    fontFamily: fontFamily.medium,
    fontSize: 13,
    color: tokens.colors.text,
  },
  convoTitleActive: {
    fontFamily: fontFamily.semibold,
    color: "#2d7058",
  },
  convoTime: {
    fontFamily: fontFamily.regular,
    fontSize: 10,
    color: tokens.colors.textMuted,
    marginTop: 2,
  },
  deleteButton: {
    padding: 6,
    borderRadius: 6,
  },
  footerProfile: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: tokens.colors.border,
  },
  avatarCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#2d7058",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    fontFamily: fontFamily.bold,
    fontSize: 14,
    color: "#FFFFFF",
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: tokens.colors.text,
  },
  userEmail: {
    fontFamily: fontFamily.regular,
    fontSize: 11,
    color: tokens.colors.textMuted,
  },
  settingsButton: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: tokens.colors.surface,
  },
});
