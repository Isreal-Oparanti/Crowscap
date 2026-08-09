import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useCallback, useEffect, useState } from "react";
import Constants, { ExecutionEnvironment } from "expo-constants";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Path } from "react-native-svg";
import { StatusBar } from "expo-status-bar";

import { createMobileSession, startEmailSession, verifyEmailSession } from "@/api/auth";
import { ApiError } from "@/api/client";
import { saveSession } from "@/auth/session";
import { BrandMark } from "@/components/shell/BrandMark";
import { Icons } from "@/components/ui/Icon";
import { useAuth } from "@/hooks/useAuth";
import { fontFamily } from "@/theme/typography";

const IOS_CLIENT_ID =
  Constants.expoConfig?.extra?.googleClientIdIos ??
  process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID_IOS ??
  "";
const WEB_CLIENT_ID =
  Constants.expoConfig?.extra?.googleClientIdWeb ??
  process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID_WEB ??
  "";



const IS_EXPO_GO = Constants.executionEnvironment === ExecutionEnvironment.StoreClient;

type AuthMode = "signup" | "login";
type BusyState = "google" | "email-start" | "email-verify" | "resend" | null;

export default function SignInScreen() {
  const { setSession } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [busy, setBusy] = useState<BusyState>(null);
  const [resendIn, setResendIn] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  const finishSignIn = useCallback(
    async (session: Awaited<ReturnType<typeof createMobileSession>>) => {
      await saveSession(session);
      setSession(session);
      router.replace("/(tabs)" as never);
    },
    [router, setSession]
  );

  async function handleGoogleSignIn() {
    setErrorMessage(null);
    if (IS_EXPO_GO) {
      setErrorMessage(
        "Expo Go cannot complete Google sign-in securely. Please use email code in Expo Go, or use a development build."
      );
      return;
    }

    if (!WEB_CLIENT_ID || (Platform.OS === "ios" && !IOS_CLIENT_ID)) {
      setErrorMessage(
        "Google sign-in is not configured. Add the Web OAuth client ID to the mobile build environment."
      );
      return;
    }

    setBusy("google");
    try {
      const { GoogleSignin } = await import("@react-native-google-signin/google-signin");
      GoogleSignin.configure({
        webClientId: WEB_CLIENT_ID,
        iosClientId: IOS_CLIENT_ID || undefined,
        scopes: ["openid", "email", "profile"],
      });

      if (Platform.OS === "android") {
        await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
      }

      // Sign out silently first so the account picker always shows
      try { await GoogleSignin.signOut(); } catch { /* ignore */ }

      const result = await GoogleSignin.signIn();
      if (result.type === "cancelled") {
        setBusy(null);
        return;
      }

      let idToken = result.data.idToken;
      if (!idToken) {
        const tokens = await GoogleSignin.getTokens();
        idToken = tokens.idToken;
      }

      if (!idToken) {
        throw new Error("Google did not return an identity token.");
      }

      await finishSignIn(
        await createMobileSession({
          id_token: idToken,
          platform: Platform.OS === "ios" ? "ios" : "android",
        })
      );
    } catch (err) {
      setErrorMessage(readableGoogleNativeError(err));
      setBusy(null);
    }
  }

  async function requestEmailCode(kind: BusyState = "email-start") {
    setErrorMessage(null);
    const normalized = email.trim().toLowerCase();
    if (!normalized || !normalized.includes("@")) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    setBusy(kind);
    try {
      const result = await startEmailSession({ email: normalized, mode });
      if (result.status === "logged_in" && result.session) {
        await finishSignIn(result.session);
        return;
      }
      setEmail(result.email);
      setCode("");
      setCodeSent(true);
      setResendIn(result.resend_after_seconds);
      setToast(`We sent a code to ${result.email}.`);
    } catch (err) {
      setErrorMessage(readableAuthError(err));
    } finally {
      setBusy(null);
    }

  }

  async function verifyEmailCode() {
    setErrorMessage(null);
    const cleanCode = code.replace(/\D/g, "");
    if (cleanCode.length !== 6) {
      setErrorMessage("Invalid verification code. Please try again.");
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
      setErrorMessage(readableAuthError(err));
    } finally {
      setBusy(null);
    }
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setCode("");
    setCodeSent(false);
    setToast(null);
    setErrorMessage(null);
  }

  const isSignup = mode === "signup";
  const headline = isSignup ? "Register" : "Log in";
  const busyNow = busy !== null;

  return (
    <View style={styles.outerRoot}>
      <StatusBar style="light" />
      <KeyboardAvoidingView
        style={styles.root}
        behavior="padding"
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
      >

        <ScrollView
          style={styles.root}
          contentContainerStyle={[
            styles.content,
            { paddingTop: insets.top + 20, paddingBottom: insets.bottom + 40 },
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >

        <View style={styles.logoWrap}>
          <BrandMark size={44} imageSize={34} />
        </View>

        <Text style={styles.heading}>{headline}</Text>
        <Text style={styles.tagline}>Your Personal Intelligent Memory</Text>

        <Pressable
          style={({ pressed }) => [
            styles.googleButton,
            pressed && !busyNow ? styles.pressed : null,
          ]}
          onPress={handleGoogleSignIn}
          disabled={busyNow}
        >
          <GoogleLogoSvg size={18} />
          <Text style={styles.googleText}>
            {busy === "google" ? "Opening Google..." : "Continue with Google"}
          </Text>
          {busy === "google" ? (
            <ActivityIndicator size="small" color="#ffffff" />
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
          <View
            style={[
              styles.inputWrap,
              errorMessage && !codeSent ? styles.inputErrorBorder : null,
            ]}
          >
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={(value) => {
                setEmail(value);
                setErrorMessage(null);
                if (codeSent) {
                  setCode("");
                  setCodeSent(false);
                }
              }}
              placeholder="Enter your email address"

              placeholderTextColor="#5a5e66"
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
                  setErrorMessage(null);
                }}
                hitSlop={8}
              >
                <Icons.X size={16} color="#8a8e94" />
              </Pressable>
            ) : null}
          </View>
          {errorMessage && !codeSent ? (
            <Text style={styles.errorText}>{errorMessage}</Text>
          ) : null}
        </View>

        {codeSent ? (
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Verification code</Text>
            <View
              style={[
                styles.inputWrap,
                errorMessage ? styles.inputErrorBorder : null,
              ]}
            >
              <TextInput
                style={styles.input}
                value={code}
                onChangeText={(value) => {
                  setCode(value.replace(/\D/g, "").slice(0, 6));
                  setErrorMessage(null);
                }}
                placeholder="676767"
                placeholderTextColor="#5a5e66"
                keyboardType="number-pad"
                editable={!busyNow}
                maxLength={6}
                returnKeyType="done"
                onSubmitEditing={verifyEmailCode}
              />
            </View>
            {errorMessage ? (
              <Text style={styles.errorText}>{errorMessage}</Text>
            ) : (
              <Text style={styles.helper}>We sent a 6-digit code to your inbox</Text>
            )}
          </View>
        ) : null}

        <Pressable
          style={({ pressed }) => [
            styles.continueButton,
            pressed && !busyNow ? styles.pressed : null,
          ]}
          onPress={() => (codeSent ? verifyEmailCode() : requestEmailCode())}
          disabled={busyNow}
        >
          {busy === "email-start" || busy === "email-verify" ? (
            <ActivityIndicator size="small" color="#0d0e11" />
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
              {resendIn > 0 ? `Resend in ${resendIn}s` : "Resend verification code"}
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
          By continuing, you acknowledge that you understand and agree to the Terms & Conditions and Privacy Policy
        </Text>
      </ScrollView>

      {toast ? (
        <View style={[styles.toast, { top: insets.top + 12 }]}>
          <View style={styles.toastIcon}>
            <Icons.Check size={16} color="#34d399" />
          </View>
          <Text style={styles.toastText}>{toast}</Text>
          <Pressable onPress={() => setToast(null)} hitSlop={8}>
            <Icons.X size={16} color="#8a8e94" />
          </Pressable>
        </View>
      ) : null}
    </KeyboardAvoidingView>
    </View>
  );
}

function readableAuthError(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }

  const msg = error instanceof Error ? error.message : String(error ?? "");
  if (error instanceof TypeError || msg.includes("Failed to fetch") || msg.includes("Network request failed")) {
    return "Crowscap could not reach the server. Please check your internet connection.";
  }

  return msg || "Something went wrong. Please try again.";
}

function readableGoogleNativeError(error: unknown) {
  if (error instanceof ApiError) {
    return readableAuthError(error);
  }

  const code =
    typeof error === "object" && error && "code" in error
      ? String((error as { code?: unknown }).code)
      : "";
  const message = error instanceof Error ? error.message : String(error ?? "");
  const lowerMessage = message.toLowerCase();

  if (code.includes("SIGN_IN_CANCELLED") || lowerMessage.includes("cancel")) {
    return "Google sign-in was cancelled.";
  }

  if (code.includes("PLAY_SERVICES_NOT_AVAILABLE")) {
    return "Google Play Services is not available or needs an update on this device.";
  }

  if (code.includes("DEVELOPER_ERROR") || lowerMessage.includes("developer_error")) {
    return "Google sign-in is not fully connected to this Android build yet. Check the Android OAuth client package name and SHA-1 in Google Cloud.";
  }

  if (error instanceof TypeError) {
    return "Crowscap could not reach the server. Please check your internet connection.";
  }

  return "Google sign-in could not complete. Try email code for now, or try again shortly.";
}

function GoogleLogoSvg({ size = 18 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <Path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <Path
        d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <Path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
        fill="#EA4335"
      />
    </Svg>
  );
}

const styles = StyleSheet.create({
  outerRoot: {
    flex: 1,
    backgroundColor: "#0d0e11",
  },
  root: {
    flex: 1,
    backgroundColor: "#0d0e11",
  },

  content: {
    flexGrow: 1,
    paddingHorizontal: 22,
  },

  logoWrap: {
    alignItems: "center",
    marginBottom: 20,
    marginTop: 10,
  },
  heading: {
    textAlign: "center",
    fontSize: 28,
    lineHeight: 34,
    fontFamily: fontFamily.bold,
    color: "#ffffff",
    letterSpacing: -0.3,
  },
  tagline: {
    marginTop: 6,
    textAlign: "center",
    fontSize: 14,
    lineHeight: 20,
    fontFamily: fontFamily.medium,
    color: "#8e9196",
  },
  googleButton: {
    marginTop: 32,
    height: 48,
    borderWidth: 1,
    borderColor: "#2a2d34",
    borderRadius: 8,
    backgroundColor: "#16181c",
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  googleText: {
    flex: 1,
    textAlign: "center",
    fontSize: 14,
    fontFamily: fontFamily.semibold,
    color: "#ffffff",
  },
  googleSpacer: {
    width: 18,
  },
  pressed: {
    opacity: 0.8,
  },
  dividerRow: {
    marginTop: 26,
    marginBottom: 24,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: "#22242a",
  },
  dividerText: {
    fontSize: 11,
    fontFamily: fontFamily.bold,
    color: "#5b5e64",
    letterSpacing: 0.5,
  },
  fieldGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 13,
    fontFamily: fontFamily.semibold,
    color: "#ffffff",
    marginBottom: 8,
  },
  inputWrap: {
    height: 48,
    borderWidth: 1,
    borderColor: "#2a2d34",
    borderRadius: 8,
    backgroundColor: "#16181c",
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
  },
  inputErrorBorder: {
    borderColor: "#ef5350",
  },
  input: {
    flex: 1,
    fontSize: 15,
    fontFamily: fontFamily.medium,
    color: "#ffffff",
    paddingVertical: Platform.OS === "ios" ? 12 : 8,
  },
  errorText: {
    marginTop: 6,
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#ef5350",
  },
  helper: {
    marginTop: 6,
    fontSize: 13,
    fontFamily: fontFamily.medium,
    color: "#777b80",
  },
  continueButton: {
    height: 48,
    borderRadius: 8,
    backgroundColor: "#ffffff",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  continueText: {
    fontSize: 15,
    fontFamily: fontFamily.bold,
    color: "#0d0e11",
  },
  resendButton: {
    alignItems: "center",
    paddingVertical: 14,
  },
  resendText: {
    fontSize: 14,
    fontFamily: fontFamily.medium,
    color: "#ffffff",
    textDecorationLine: "underline",
  },
  modeRow: {
    marginTop: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  modeText: {
    fontSize: 14,
    fontFamily: fontFamily.medium,
    color: "#8e9196",
  },
  modeLink: {
    fontSize: 14,
    fontFamily: fontFamily.bold,
    color: "#ffffff",
  },
  terms: {
    marginTop: 42,
    textAlign: "center",
    fontSize: 12,
    lineHeight: 18,
    fontFamily: fontFamily.regular,
    color: "#60646a",
    paddingHorizontal: 12,
  },
  toast: {
    position: "absolute",
    left: 20,
    right: 20,
    height: 52,
    borderRadius: 12,
    backgroundColor: "#1c1e24",
    borderWidth: 1,
    borderColor: "#2c2f38",
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
    shadowColor: "#000000",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
    zIndex: 100,
  },

  toastIcon: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 1.5,
    borderColor: "#34d399",
    alignItems: "center",
    justifyContent: "center",
  },
  toastText: {
    flex: 1,
    fontSize: 13.5,
    fontFamily: fontFamily.medium,
    color: "#d1d5db",
  },
});
