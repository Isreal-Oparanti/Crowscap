/** Expo Router route constants for use with router.push / router.replace. */
export const ROUTES = {
  SIGN_IN: "/sign-in" as const,
  CHAT: "/(tabs)/" as const,
  RECALL: "/(tabs)/recall" as const,
  SEARCH: "/(tabs)/search" as const,
  SETTINGS: "/settings" as const,
  CAPTURE: "/(modals)/capture" as const,
  CAPTURE_RESULT: "/(modals)/capture-result" as const,
  MEMORY_DETAIL: (id: string) => `/(modals)/memory/${id}` as const,
} as const;
