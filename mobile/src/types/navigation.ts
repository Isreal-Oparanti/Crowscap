/**
 * Typed route names for Expo Router navigation.
 * Keep in sync with the app/ directory structure.
 */

export type RootRoute = "/sign-in" | "/(tabs)" | "/settings" | "/(modals)/capture" | "/(modals)/capture-result";

export type TabRoute =
  | "/(tabs)/"
  | "/(tabs)/recall"
  | "/(tabs)/search";

export type ModalRoute =
  | "/(modals)/capture"
  | "/(modals)/capture-result"
  | `/(modals)/memory/${string}`;
