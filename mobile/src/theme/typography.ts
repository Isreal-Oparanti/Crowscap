export const fontFamily = {
  regular: "Manrope_400Regular",
  medium: "Manrope_500Medium",
  semibold: "Manrope_600SemiBold",
  bold: "Manrope_700Bold",
  extrabold: "Manrope_800ExtraBold",
} as const;

export const type = {
  eyebrow: {
    fontFamily: fontFamily.extrabold,
    fontSize: 11,
    letterSpacing: 0,
  },
  body: {
    fontFamily: fontFamily.medium,
    fontSize: 13,
    lineHeight: 20,
    letterSpacing: 0,
  },
  bodyLarge: {
    fontFamily: fontFamily.medium,
    fontSize: 15,
    lineHeight: 23,
    letterSpacing: 0,
  },
  title: {
    fontFamily: fontFamily.extrabold,
    fontSize: 18,
    lineHeight: 24,
    letterSpacing: 0,
  },
  pageTitle: {
    fontFamily: fontFamily.extrabold,
    fontSize: 30,
    lineHeight: 36,
    letterSpacing: 0,
  },
} as const;
