import { useEffect } from "react";
import { useRouter } from "expo-router";
import { useShareIntent } from "@/hooks/useShareIntent";

/**
 * Global ShareIntentHandler component.
 * Placed in the RootLayout to catch incoming share sheets from other apps.
 */
export function ShareIntentHandler() {
  const router = useRouter();
  const { hasShareIntent, content, clear } = useShareIntent();

  useEffect(() => {
    if (hasShareIntent && content?.text) {
      const shareText = content.text;
      clear();
      router.push({
        pathname: "/(modals)/capture",
        params: { initialContent: shareText },
      });
    }
  }, [hasShareIntent, content, clear, router]);

  return null;
}
