import { Platform } from "react-native";

/**
 * Platform-aware shadow presets.
 * iOS uses shadow* props; Android uses elevation.
 */
export const shadows = {
  sm: Platform.select({
    ios: {
      shadowColor: "#111111",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.04,
      shadowRadius: 3,
    },
    android: { elevation: 1 },
  }),
  md: Platform.select({
    ios: {
      shadowColor: "#111111",
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.06,
      shadowRadius: 10,
    },
    android: { elevation: 3 },
  }),
  lg: Platform.select({
    ios: {
      shadowColor: "#111111",
      shadowOffset: { width: 0, height: 10 },
      shadowOpacity: 0.08,
      shadowRadius: 24,
    },
    android: { elevation: 6 },
  }),
};
