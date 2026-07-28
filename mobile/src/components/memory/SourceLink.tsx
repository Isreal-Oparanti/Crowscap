import { Text, StyleSheet, Pressable, Linking } from "react-native";
import { Feather } from "@expo/vector-icons";

export function SourceLink({
  title,
  url,
  type = "text",
}: {
  title?: string | null;
  url?: string | null;
  type?: string;
}) {
  if (!title && !url) return null;

  const handleOpenUrl = () => {
    if (url) {
      Linking.openURL(url).catch(() => null);
    }
  };

  return (
    <Pressable
      style={({ pressed }) => [
        styles.container,
        pressed && url && { opacity: 0.75 },
      ]}
      onPress={url ? handleOpenUrl : undefined}
      disabled={!url}
    >
      <Feather name="file-text" size={12} color="#7d8083" />
      <Text style={styles.title} numberOfLines={1}>
        {title || url || "Original Source"}
      </Text>
      {url ? <Feather name="external-link" size={11} color="#7d8083" /> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#f5f6f7",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    alignSelf: "flex-start",
    maxWidth: "100%",
  },
  title: {
    fontSize: 11,
    fontWeight: "600",
    color: "#555860",
    flexShrink: 1,
  },
});
