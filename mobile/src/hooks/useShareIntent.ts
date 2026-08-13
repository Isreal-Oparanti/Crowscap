import { useShareIntent as useExpoShareIntent } from "expo-share-intent";
import { useCallback, useMemo } from "react";

export interface SharedContent {
  text?: string;
  url?: string;
  type?: "media" | "file" | "text" | "weburl" | null;
}

export function useShareIntent() {
  const { hasShareIntent, shareIntent, resetShareIntent, error } = useExpoShareIntent();

  const clear = useCallback(() => {
    resetShareIntent();
  }, [resetShareIntent]);

  const content: SharedContent | null = useMemo(() => {
    if (!hasShareIntent || !shareIntent) return null;
    const shareValue = shareIntent.webUrl || shareIntent.text || undefined;
    return {
      text: shareValue,
      url: shareIntent.type === "weburl" ? (shareIntent.webUrl || shareValue) : undefined,
      type: shareIntent.type as SharedContent["type"],
    };
  }, [hasShareIntent, shareIntent]);

  return {
    hasShareIntent,
    content,
    clear,
    error,
  };
}
