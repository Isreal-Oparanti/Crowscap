import { StyleSheet } from "react-native";
import { tokens } from "./tokens";

/**
 * Typography style presets.
 * Use these instead of defining font styles ad-hoc in components.
 */
export const typography = StyleSheet.create({
  label: {
    fontSize: tokens.fontSize.xs,
    fontWeight: tokens.fontWeight.extrabold,
    letterSpacing: 0.5,
    textTransform: "uppercase",
    color: tokens.colors.textMuted,
  },
  caption: {
    fontSize: tokens.fontSize.xs,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.textSubtle,
  },
  body: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.regular,
    color: tokens.colors.text,
    lineHeight: tokens.lineHeight.normal,
  },
  bodyMedium: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
    lineHeight: tokens.lineHeight.normal,
  },
  subheading: {
    fontSize: tokens.fontSize.md,
    fontWeight: tokens.fontWeight.bold,
    color: tokens.colors.text,
    lineHeight: tokens.lineHeight.tight,
  },
  heading: {
    fontSize: tokens.fontSize.lg,
    fontWeight: tokens.fontWeight.bold,
    color: tokens.colors.text,
    lineHeight: tokens.lineHeight.tight,
  },
  title: {
    fontSize: tokens.fontSize["2xl"],
    fontWeight: tokens.fontWeight.extrabold,
    color: tokens.colors.text,
    lineHeight: 34,
  },
});
