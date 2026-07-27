import { View, Text, StyleSheet, Pressable } from "react-native";
import { tokens } from "@/theme/tokens";

// TODO: Implement Google OAuth sign-in using expo-auth-session
export default function SignInScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.logo}>Crowscap</Text>
      <Text style={styles.tagline}>
        Turn what you save into knowledge you can use.
      </Text>
      <Pressable style={styles.button}>
        <Text style={styles.buttonText}>Continue with Google</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: tokens.colors.background,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: tokens.spacing[6],
  },
  logo: {
    fontSize: 32,
    fontWeight: "700",
    color: tokens.colors.text,
    marginBottom: tokens.spacing[2],
  },
  tagline: {
    fontSize: 14,
    color: tokens.colors.textMuted,
    textAlign: "center",
    marginBottom: tokens.spacing[10],
    lineHeight: 22,
  },
  button: {
    backgroundColor: tokens.colors.text,
    paddingVertical: tokens.spacing[4],
    paddingHorizontal: tokens.spacing[8],
    borderRadius: tokens.radius.md,
    width: "100%",
    alignItems: "center",
  },
  buttonText: {
    color: tokens.colors.background,
    fontWeight: "600",
    fontSize: 15,
  },
});
