import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useEffect, useMemo, useState } from "react";
import { Feather } from "@expo/vector-icons";
import * as AuthSession from "expo-auth-session";
import * as Crypto from "expo-crypto";
import Constants from "expo-constants";
import * as WebBrowser from "expo-web-browser";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { createMobileSession, startEmailSession, verifyEmailSession } from "@/api/auth";
import { ApiError } from "@/api/client";
import { saveSession } from "@/auth/session";
import { BrandMark } from "@/components/shell/BrandMark";
import { useAuth } from "@/hooks/useAuth";
import { tokens } from "@/theme/tokens";

WebBrowser.maybeCompleteAuthSession();

const IOS_CLIENT_ID =
  Constants.expoConfig?.extra?.googleClientIdIos ??
  process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID_IOS ??
  "";
const ANDROID_CLIENT_ID =
  Constants.expoConfig?.extra?.googleClientIdAndroid ??
  process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID_ANDROID ??
  "";

const CLIENT_ID = Platform.OS === "ios" ? IOS_CLIENT_ID : ANDROID_CLIENT_ID;

const googleDiscovery = {
  authorizationEndpoint: "https://accounts.google.com/o/oauth2/v2/auth",
  tokenEndpoint: "https://oauth2.googleapis.com/token",
};

type AuthMode = "signup" | "login";
type BusyState = "google" | "email-start" | "email-verify" | "resend" | null;

export default function SignInScreen() {
  const { setSession } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [mode, setMode] = useState<AuthMode>("signup");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [busy, setBusy] = useState<BusyState>(null);
  const [resendIn, setResendIn] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const nonce = useMemo(() => Crypto.randomUUID(), []);

  const redirectUri = AuthSession.makeRedirectUri({
    scheme: "crowscap",
    path: "auth",
  });

  const [, , promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: CLIENT_ID,
      redirectUri,
      scopes: ["openid", "email", "profile"],
      responseType: AuthSession.ResponseType.IdToken,
      extraParams: { nonce },
    },
    googleDiscovery
  );

  useEffect(() => {
    if (!resendIn) return;
    const timer = setInterval(() => {
      setResendIn((value) => Math.max(0, value - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendIn]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4200);
    return () => clearTimeout(timer);
  }, [toast]);

  async function finishSignIn(session: Awaited<ReturnType<typeof createMobileSession>>) {
    await saveSession(session);
    setSession(session);
    router.replace("/(tabs)" as never);
  }

  async function handleGoogleSignIn() {
    if (!CLIENT_ID) {
      Alert.alert(
        "Google sign in is not configured",
        "Add the mobile Google OAuth client ID to the app environment, then try again."
      );
      return;
    }

    setBusy("google");
    try {
      const result = await promptAsync();
      if (result?.type !== "success") return;

      const idToken = result.params.id_token;
      if (!idToken) {
        Alert.alert("Sign in failed", "Google did not return a valid identity token.");
        return;
      }

      const session = await createMobileSession({
        id_token: idToken,
        platform: Platform.OS === "ios" ? "ios" : "android",
      });
      await finishSignIn(session);
    } catch (err) {
      Alert.alert("Sign in failed", readableAuthError(err));
    } finally {
      setBusy(null);
    }
  }

  async function requestEmailCode(kind: BusyState = "email-start") {
    const normalized = email.trim().toLowerCase();
    if (!normalized || !normalized.includes("@")) {
      Alert.alert("Email required", "Enter the email you want to use for Crowscap.");
      return;
    }

    setBusy(kind);
    try {
      const result = await startEmailSession({ email: normalized, mode });
      setEmail(result.email);
      setCode("");
      setCodeSent(true);
      setResendIn(result.resend_after_seconds);
      setToast(`We sent a code to ${result.email}.`);
    } catch (err) {
      Alert.alert("Code could not send", readableAuthError(err));
    } finally {
      setBusy(null);
    }
  }

  async function verifyEmailCode() {
    const cleanCode = code.replace(/\D/g, "");
    if (cleanCode.length !== 6) {
      Alert.alert("Enter the code", "Use the 6-digit code we sent to your inbox.");
      return;
    }

    setBusy("email-verify");
    try {
      const session = await verifyEmailSession({
        email: email.trim().toLowerCase(),
        code: cleanCode,
        mode,
      });
      await finishSignIn(session);
    } catch (err) {
      Alert.alert("Code did not work", readableAuthError(err));
    } finally {
      setBusy(null);
    }
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setCode("");
    setCodeSent(false);
    setToast(null);
  }

  const isSignup = mode === "signup";
  const headline = isSignup ? "Sign Up" : "Log in";
  const busyNow = busy !== null;

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        style={styles.root}
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + 46, paddingBottom: insets.bottom + 28 },
        ]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.logoWrap}>
          <BrandMark size={58} imageSize={44} />
        </View>

        <Text style={styles.heading}>{headline}</Text>
        <Text style={styles.tagline}>Turn your knowledge into your edge</Text>

        <Pressable
          style={({ pressed }) => [styles.googleButton, pressed && !busyNow ? styles.pressed : null]}
          onPress={handleGoogleSignIn}
          disabled={busyNow}
        >
          <GoogleMark />
          <Text style={styles.googleText}>
            {busy === "google" ? "Opening Google..." : "Continue with Google"}
          </Text>
          {busy === "google" ? (
            <ActivityIndicator size="small" color={tokens.colors.text} />
          ) : (
            <View style={styles.googleSpacer} />
          )}
        </Pressable>

        <View style={styles.dividerRow}>
          <View style={styles.divider} />
          <Text style={styles.dividerText}>OR</Text>
          <View style={styles.divider} />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Email</Text>
          <View style={styles.inputWrap}>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={(value) => {
                setEmail(value);
                if (codeSent) {
                  setCode("");
                  setCodeSent(false);
                }
              }}
              placeholder="Enter your email address..."
              placeholderTextColor="#a9abae"
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              editable={!busyNow}
              returnKeyType={codeSent ? "next" : "send"}
              onSubmitEditing={() => {
                if (!codeSent) void requestEmailCode();
              }}
            />
            {email ? (
              <Pressable
                onPress={() => {
                  setEmail("");
                  setCode("");
                  setCodeSent(false);
                }}
                hitSlop={8}
              >
                <Feather name="x" size={20} color="#696d70" />
              </Pressable>
            ) : null}
          </View>
        </View>

        {codeSent ? (
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Verification code</Text>
            <View style={styles.inputWrap}>
              <TextInput
                style={styles.input}
                value={code}
                onChangeText={(value) => setCode(value.replace(/\D/g, "").slice(0, 6))}
                placeholder="Enter code"
                placeholderTextColor="#a9abae"
                keyboardType="number-pad"
                editable={!busyNow}
                maxLength={6}
                returnKeyType="done"
                onSubmitEditing={verifyEmailCode}
              />
            </View>
            <Text style={styles.helper}>We sent a code to your inbox</Text>
          </View>
        ) : null}

        <Pressable
          style={({ pressed }) => [styles.continueButton, pressed && !busyNow ? styles.pressed : null]}
          onPress={() => (codeSent ? verifyEmailCode() : requestEmailCode())}
          disabled={busyNow}
        >
          {busy === "email-start" || busy === "email-verify" ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <Text style={styles.continueText}>Continue</Text>
          )}
        </Pressable>

        {codeSent ? (
          <Pressable
            disabled={resendIn > 0 || busyNow}
            onPress={() => requestEmailCode("resend")}
            style={styles.resendButton}
          >
            <Text style={styles.resendText}>
              {resendIn > 0 ? `Resend in ${resendIn}s` : "Resend code"}
            </Text>
          </Pressable>
        ) : null}

        <View style={styles.modeRow}>
          <Text style={styles.modeText}>
            {isSignup ? "Already have an account?" : "Don't have an account?"}
          </Text>
          <Pressable onPress={() => switchMode(isSignup ? "login" : "signup")}>
            <Text style={styles.modeLink}>{isSignup ? "Log in" : "Sign up"}</Text>
          </Pressable>
        </View>

        <Text style={styles.terms}>
          By continuing, you acknowledge that you understand and agree to the Terms & Conditions and Privacy Policy.
        </Text>
      </ScrollView>

      {toast ? (
        <View style={[styles.toast, { bottom: insets.bottom + 18 }]}>
          <View style={styles.toastIcon}>
            <Feather name="check" size={20} color="#2d7058" />
          </View>
          <Text style={styles.toastText}>{toast}</Text>
          <Pressable onPress={() => setToast(null)} hitSlop={8}>
            <Feather name="x" size={20} color="#4b4f52" />
          </Pressable>
        </View>
      ) : null}
    </KeyboardAvoidingView>
  );
}

function readableAuthError(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof TypeError) {
    return "Crowscap could not reach the backend. Check your internet connection and try again.";
  }

  return error instanceof Error ? error.message : "Something went wrong. Try again.";
}

function GoogleMark() {
  return (
    <View style={styles.googleMark}>
      <Text style={styles.googleG}>G</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  content: {
    minHeight: "100%",
    paddingHorizontal: 28,
  },
  logoWrap: {
    alignItems: "center",
    marginBottom: 30,
  },
  heading: {
    textAlign: "center",
    fontSize: 35,
    lineHeight: 40,
    fontWeight: "900",
    color: tokens.colors.text,
    letterSpacing: -0.7,
  },
  tagline: {
    marginTop: 24,
    textAlign: "center",
    fontSize: 16,
    lineHeight: 22,
    fontWeight: "500",
    color: "#777b7e",
  },
  googleButton: {
    marginTop: 76,
    minHeight: 58,
    borderWidth: 1,
    borderColor: "#dfe1e2",
    borderRadius: 999,
    backgroundColor: "#ffffff",
    paddingHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.05,
    shadowRadius: 18,
    elevation: 2,
  },
  googleText: {
    flex: 1,
    textAlign: "center",
    fontSize: 16,
    fontWeight: "800",
    color: tokens.colors.text,
  },
  googleSpacer: {
    width: 28,
  },
  googleMark: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ffffff",
  },
  googleG: {
    fontSize: 18,
    fontWeight: "900",
    color: "#4285f4",
  },
  pressed: {
    opacity: 0.75,
    transform: [{ scale: 0.995 }],
  },
  dividerRow: {
    marginTop: 54,
    marginBottom: 46,
    flexDirection: "row",
    alignItems: "center",
    gap: 18,
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: "#e5e6e7",
  },
  dividerText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#777b7e",
  },
  fieldGroup: {
    gap: 12,
    marginBottom: 24,
  },
  label: {
    fontSize: 15,
    fontWeight: "800",
    color: "#676b6f",
  },
  inputWrap: {
    minHeight: 66,
    borderWidth: 1,
    borderColor: "#cfd2d4",
    borderRadius: 14,
    backgroundColor: "#ffffff",
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
  },
  input: {
    flex: 1,
    fontSize: 19,
    lineHeight: 24,
    fontWeight: "600",
    color: tokens.colors.text,
    paddingVertical: Platform.OS === "ios" ? 18 : 12,
  },
  helper: {
    marginTop: -6,
    fontSize: 14,
    fontWeight: "500",
    color: "#777b7e",
  },
  continueButton: {
    minHeight: 60,
    borderRadius: 999,
    backgroundColor: tokens.colors.text,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  continueText: {
    fontSize: 18,
    fontWeight: "900",
    color: "#ffffff",
  },
  resendButton: {
    alignItems: "center",
    paddingVertical: 28,
  },
  resendText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#6e7275",
  },
  modeRow: {
    marginTop: 30,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
  },
  modeText: {
    fontSize: 16,
    lineHeight: 22,
    fontWeight: "700",
    color: "#6e7275",
  },
  modeLink: {
    fontSize: 16,
    lineHeight: 22,
    fontWeight: "900",
    color: tokens.colors.text,
  },
  terms: {
    marginTop: 90,
    textAlign: "center",
    fontSize: 13,
    lineHeight: 24,
    fontWeight: "500",
    color: "#a0a3a6",
  },
  toast: {
    position: "absolute",
    left: 24,
    right: 24,
    minHeight: 72,
    borderRadius: 22,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#eceeef",
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 20,
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 18 },
    shadowOpacity: 0.15,
    shadowRadius: 30,
    elevation: 8,
  },
  toastIcon: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 2,
    borderColor: "#85caa8",
    alignItems: "center",
    justifyContent: "center",
  },
  toastText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 21,
    fontWeight: "600",
    color: "#4b4f52",
  },
});
