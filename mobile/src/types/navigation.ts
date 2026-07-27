/**
 * Typed route names for Expo Router navigation.
 * Keep in sync with the app/ directory structure.
 */

export type RootRoute = "/sign-in" | "/(tabs)" | "/(modals)/capture" | "/(modals)/capture-result";

export type TabRoute =
  | "/(tabs)/"
  | "/(tabs)/recall"
  | "/(tabs)/search"
  | "/(tabs)/settings";

export type ModalRoute =
  | "/(modals)/capture"
  | "/(modals)/capture-result"
  | `/(modals)/memory/${string}`;
