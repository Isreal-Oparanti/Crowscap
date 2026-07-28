import { useCallback, useMemo } from "react";

export interface SharedContent {
  text?: string;
  url?: string;
  type?: "media" | "file" | "text" | "weburl" | null;
}

export function useShareIntent() {
  const clear = useCallback(() => {}, []);

  return useMemo(
    () => ({
      hasShareIntent: false,
      content: null as SharedContent | null,
      clear,
      error: null as unknown,
    }),
    [clear]
  );
}
