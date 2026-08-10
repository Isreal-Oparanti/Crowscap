import { Linking, StyleSheet, Text, View } from "react-native";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";

type MarkdownTextProps = {
  text: string;
  compact?: boolean;
};

type Block =
  | { type: "heading"; text: string }
  | { type: "paragraph"; lines: string[] }
  | { type: "list"; ordered: boolean; items: string[] };

const inlinePattern =
  /(\[[^\]]+\]\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s<]+|`[^`\n]+`|\*\*[^*\n]+?\*\*|__[^_\n]+?__|\*[^*\n]+?\*|_[^_\n]+?_)/g;

export function MarkdownText({ text, compact = false }: MarkdownTextProps) {
  const blocks = parseBlocks(normalizeDisplayText(text));
  if (blocks.length === 0) return null;

  return (
    <View style={styles.root}>
      {blocks.map((block, index) => {
        const spacing = index === 0 ? null : compact ? styles.compactGap : styles.gap;

        if (block.type === "heading") {
          return (
            <Text key={index} style={[styles.heading, spacing]}>
              {renderInline(block.text, true)}
            </Text>
          );
        }

        if (block.type === "list") {
          return (
            <View key={index} style={[styles.list, spacing]}>
              {block.items.map((item, itemIndex) => (
                <View key={`${item}-${itemIndex}`} style={styles.listItem}>
                  <Text style={styles.bullet}>{block.ordered ? `${itemIndex + 1}.` : "•"}</Text>
                  <Text style={[styles.text, compact && styles.compactText, styles.listItemText]}>
                    {renderInline(item)}
                  </Text>
                </View>
              ))}
            </View>
          );
        }


        return (
          <Text key={index} style={[styles.text, compact && styles.compactText, spacing]}>
            {block.lines.map((line, lineIndex) => (
              <Text key={`${line}-${lineIndex}`}>
                {lineIndex && !compact ? "\n" : lineIndex ? " " : ""}
                {renderInline(line)}
              </Text>
            ))}
          </Text>
        );
      })}
    </View>
  );
}

export function normalizeDisplayText(value: string): string {
  return value
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]*[\u2014\u2013][ \t]*/g, " - ")
    .replace(/([.!?])(?=[A-Z][a-z]{2,})/g, "$1 ")
    .replace(
      /([^\n])(?=(?:What is still missing|Ideas worth comparing|Useful next move|What I know|Why it matters)\s*:)/gi,
      "$1\n\n",
    )
    .replace(
      /^(What is still missing|Ideas worth comparing|Useful next move|What I know|Why it matters)\s*:/gim,
      "### $1",
    )
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function parseBlocks(text: string): Block[] {
  if (!text) return [];

  const blocks: Block[] = [];
  const lines = text.split("\n");
  let paragraph: string[] = [];
  let list: Extract<Block, { type: "list" }> | null = null;

  const flushParagraph = () => {
    if (paragraph.length > 0) blocks.push({ type: "paragraph", lines: paragraph });
    paragraph = [];
  };

  const flushList = () => {
    if (list) blocks.push(list);
    list = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = line.match(/^#{1,3}\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", text: heading[1] });
      continue;
    }

    const listMatch = line.match(/^([-*+•]\s+|\d+[.)]\s+)(.+)$/);
    if (listMatch) {
      flushParagraph();
      const ordered = /^\d/.test(listMatch[1]);
      if (!list || list.ordered !== ordered) {
        flushList();
        list = { type: "list", ordered, items: [] };
      }
      list.items.push(listMatch[2]);
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();
  return blocks;
}

function renderInline(text: string, strong = false) {
  return text
    .split(inlinePattern)
    .filter(Boolean)
    .map((part, index) => {
      const markdownLink = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
      const bareLink = part.match(/^https?:\/\/[^\s<]+$/);
      if (markdownLink || bareLink) {
        const href = markdownLink?.[2] ?? part.replace(/[),.;!?]+$/, "");
        const label = markdownLink?.[1] ?? readableUrl(href);
        return (
          <Text
            key={`${part}-${index}`}
            style={styles.link}
            onPress={() => Linking.openURL(href).catch(() => undefined)}
          >
            {label}
          </Text>
        );
      }

      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <Text key={`${part}-${index}`} style={styles.code}>
            {part.slice(1, -1)}
          </Text>
        );
      }

      if (
        (part.startsWith("**") && part.endsWith("**")) ||
        (part.startsWith("__") && part.endsWith("__"))
      ) {
        return (
          <Text key={`${part}-${index}`} style={styles.bold}>
            {part.slice(2, -2)}
          </Text>
        );
      }

      if (
        (part.startsWith("*") && part.endsWith("*")) ||
        (part.startsWith("_") && part.endsWith("_"))
      ) {
        return (
          <Text key={`${part}-${index}`} style={styles.italic}>
            {part.slice(1, -1)}
          </Text>
        );
      }

      return (
        <Text key={`${part}-${index}`} style={strong ? styles.bold : null}>
          {part}
        </Text>
      );
    });
}

function readableUrl(value: string): string {
  const cleaned = value.replace(/^https?:\/\//, "").replace(/^www\./, "");
  const [withoutQuery] = cleaned.split(/[?#]/);
  const shortened = withoutQuery.length > 46 ? `${withoutQuery.slice(0, 43)}...` : withoutQuery;
  return shortened || value;
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    flexShrink: 1,
    width: "100%",
  },
  gap: {
    marginTop: 12,
  },
  compactGap: {
    marginTop: 7,
  },
  text: {
    fontSize: 14.5,
    lineHeight: 23,
    fontFamily: fontFamily.medium,
    color: "#1a1c1e",
    flexWrap: "wrap",
  },
  compactText: {
    fontSize: 13,
    lineHeight: 20,
    color: "#203a2e",
  },

  heading: {
    fontSize: 15,
    lineHeight: 22,
    fontFamily: fontFamily.extrabold,
    color: "#111418",
    marginTop: 4,
    marginBottom: 2,
    flexWrap: "wrap",
  },
  list: {
    gap: 8,
    marginTop: 8,
    marginBottom: 8,
  },
  listItem: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    paddingLeft: 2,
  },
  listItemText: {
    flex: 1,
  },
  bullet: {
    width: 14,
    fontSize: 15,
    lineHeight: 23,
    fontFamily: fontFamily.extrabold,
    color: "#1a1c1e",
  },

  link: {
    color: tokens.colors.text,
    textDecorationLine: "underline",
    textDecorationColor: "#b7bbbd",
    fontFamily: fontFamily.bold,
  },
  bold: {
    fontFamily: fontFamily.extrabold,
    color: tokens.colors.text,
  },
  italic: {
    fontStyle: "italic",
  },
  code: {
    fontFamily: "monospace",
    backgroundColor: "#f0f1f2",
    color: tokens.colors.text,
  },
});
