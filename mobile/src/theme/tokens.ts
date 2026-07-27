/**
 * Crowscap Mobile Design Tokens
 * Mirrors the web product's visual identity, adapted for React Native.
 */

export const tokens = {
  colors: {
    // Core
    background: "#ffffff",
    backgroundDark: "#0f0f0f",
    surface: "#fafafa",
    surfaceDark: "#1a1a1a",
    border: "#e1e3e4",
    borderDark: "#2a2a2a",

    // Text
    text: "#111111",
    textMuted: "#7e8285",
    textSubtle: "#adb0b2",

    // Brand
    accent: "#111111",
    accentMuted: "#4d5255",

    // Semantic
    success: "#2d7058",
    warning: "#b07030",
    danger: "#9b4c51",
    info: "#356b8f",

    // Memory type badge backgrounds
    badgePrinciple: "#eef4f7",
    badgeClaim: "#f4f0f7",
    badgeWarning: "#f7f0ee",
    badgeAction: "#eef7f1",
    badgeQuestion: "#f7f7ee",
  },

  spacing: {
    0: 0,
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    5: 20,
    6: 24,
    7: 28,
    8: 32,
    9: 36,
    10: 40,
    12: 48,
    14: 56,
    16: 64,
  },

  radius: {
    sm: 6,
    md: 10,
    lg: 14,
    xl: 20,
    full: 9999,
  },

  fontSize: {
    xs: 10,
    sm: 11,
    base: 13,
    md: 15,
    lg: 18,
    xl: 22,
    "2xl": 27,
    "3xl": 32,
  },

  fontWeight: {
    regular: "400" as const,
    medium: "500" as const,
    semibold: "600" as const,
    bold: "700" as const,
    extrabold: "800" as const,
  },

  lineHeight: {
    tight: 18,
    normal: 22,
    relaxed: 26,
  },
} as const;

export type Tokens = typeof tokens;
