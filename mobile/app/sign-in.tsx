import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useMemo, useState, type ReactNode } from "react";
import { Feather } from "@expo/vector-icons";
import * as AuthSession from "expo-auth-session";
import * as Crypto from "expo-crypto";
import Constants from "expo-constants";
import * as WebBrowser from "expo-web-browser";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { createDemoSession, createMobileSession } from "@/api/auth";
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

type SignInProvider = "google" | "demo" | null;

export default function SignInScreen() {
  const { setSession } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [signingInProvider, setSigningInProvider] = useState<SignInProvider>(null);
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

    setSigningInProvider("google");
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
      Alert.alert("Sign in failed", readableAuthError(err, "google"));
    } finally {
      setSigningInProvider(null);
    }
  }

  async function handleDemoSignIn() {
    setSigningInProvider("demo");
    try {
      const session = await createDemoSession({
        platform: Platform.OS === "ios" ? "ios" : "android",
      });
      await finishSignIn(session);
    } catch (err) {
      Alert.alert("Demo could not open", readableAuthError(err, "demo"));
    } finally {
      setSigningInProvider(null);
    }
  }

  const busy = signingInProvider !== null;

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[
        styles.content,
        { paddingTop: insets.top + 34, paddingBottom: insets.bottom + 28 },
      ]}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.topBar}>
        <BrandMark size={54} imageSize={44} />
        <View style={styles.privatePill}>
          <Feather name="lock" size={13} color="#4f5356" />
          <Text style={styles.privateText}>Private workspace</Text>
        </View>
      </View>

      <View style={styles.brandBlock}>
        <Text style={styles.productName}>Crowscap</Text>
        <Text style={styles.productSub}>Personal intelligence</Text>
      </View>

      <View style={styles.panel}>
        <Text style={styles.eyebrow}>Sign in</Text>
        <Text style={styles.title}>Open your memory.</Text>
        <Text style={styles.body}>
          Keep your saved ideas, sources, reminders, and recalls tied to one private
          workspace.
        </Text>

        <View style={styles.authGroup}>
          <AuthButton
            label={
              signingInProvider === "google" ? "Opening Google..." : "Continue with Google"
            }
            icon={<GoogleMark />}
            onPress={handleGoogleSignIn}
            disabled={busy}
            loading={signingInProvider === "google"}
          />
          <AuthButton
            label={
              signingInProvider === "demo" ? "Opening demo..." : "Open demo workspace"
            }
            icon={<Feather name="play-circle" size={19} color={tokens.colors.text} />}
            onPress={handleDemoSignIn}
            disabled={busy}
            loading={signingInProvider === "demo"}
          />
        </View>

        <Text style={styles.note}>
          Google is only used to identify your workspace. Your memory stays separated
          from every other user.
        </Text>
      </View>

      <View style={styles.footer}>
        <View style={styles.footerLine} />
        <Text style={styles.footerText}>Capture. Ask. Recall.</Text>
      </View>
    </ScrollView>
  );
}

function readableAuthError(error: unknown, provider: "google" | "demo") {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return provider === "demo"
        ? "The mobile demo endpoint is not live on this backend yet. Deploy the latest backend, then try again."
        : "The mobile auth endpoint is not live on this backend yet. Deploy the latest backend, then try again.";
    }
    if (error.status === 401 || error.status === 403) {
      return "The backend rejected this sign in. Check the mobile OAuth client ID and backend auth environment.";
    }
    return error.message;
  }

  if (error instanceof TypeError) {
    return "Crowscap could not reach the backend. Check your internet connection and try again.";
  }

  return error instanceof Error ? error.message : "Something went wrong. Try again.";
}

function AuthButton({
  label,
  icon,
  onPress,
  disabled,
  loading,
}: {
  label: string;
  icon: ReactNode;
  onPress: () => void;
  disabled: boolean;
  loading: boolean;
}) {
  return (
    <Pressable
      style={({ pressed }) => [
        styles.authButton,
        pressed && !disabled ? styles.authButtonPressed : null,
        disabled ? styles.authButtonDisabled : null,
      ]}
      onPress={onPress}
      disabled={disabled}
    >
      <View style={styles.authButtonIcon}>{icon}</View>
      <Text style={styles.authButtonText}>{label}</Text>
      <View style={styles.authButtonRight}>
        {loading ? (
          <ActivityIndicator size="small" color={tokens.colors.text} />
        ) : (
          <Feather name="arrow-right" size={19} color={tokens.colors.text} />
        )}
      </View>
    </Pressable>
  );
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
    backgroundColor: "#f5f5f3",
  },
  content: {
    minHeight: "100%",
    paddingHorizontal: 26,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 14,
  },
  privatePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    borderWidth: 1,
    borderColor: "#d9dcde",
    backgroundColor: "#ffffff",
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  privateText: {
    fontSize: 11,
    fontWeight: "800",
    color: "#4f5356",
    textTransform: "uppercase",
  },
  brandBlock: {
    marginTop: 22,
  },
  productName: {
    fontSize: 31,
    lineHeight: 35,
    fontWeight: "900",
    color: tokens.colors.text,
    letterSpacing: -0.8,
  },
  productSub: {
    marginTop: 3,
    fontSize: 15,
    lineHeight: 21,
    fontWeight: "600",
    color: "#73777a",
  },
  panel: {
    marginTop: 42,
    borderWidth: 1,
    borderColor: "#dfe1e2",
    backgroundColor: "#ffffff",
    borderRadius: 24,
    paddingHorizontal: 20,
    paddingVertical: 22,
    shadowColor: "#111111",
    shadowOffset: { width: 0, height: 18 },
    shadowOpacity: 0.08,
    shadowRadius: 34,
    elevation: 5,
  },
  eyebrow: {
    fontSize: 11,
    lineHeight: 15,
    fontWeight: "900",
    color: "#6f7376",
    textTransform: "uppercase",
    letterSpacing: 1.3,
  },
  title: {
    marginTop: 18,
    fontSize: 40,
    lineHeight: 42,
    fontWeight: "900",
    color: tokens.colors.text,
    letterSpacing: -1.2,
  },
  body: {
    marginTop: 14,
    fontSize: 15,
    lineHeight: 25,
    fontWeight: "500",
    color: "#4b5053",
  },
  authGroup: {
    gap: 12,
    marginTop: 26,
  },
  authButton: {
    minHeight: 56,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#d4d7d9",
    backgroundColor: "#ffffff",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
  },
  authButtonPressed: {
    backgroundColor: "#f6f7f7",
    borderColor: "#a9aeb1",
  },
  authButtonDisabled: {
    opacity: 0.68,
  },
  authButtonIcon: {
    width: 30,
    alignItems: "flex-start",
  },
  authButtonText: {
    flex: 1,
    textAlign: "center",
    fontSize: 14,
    lineHeight: 19,
    fontWeight: "800",
    color: tokens.colors.text,
  },
  authButtonRight: {
    width: 30,
    alignItems: "flex-end",
  },
  googleMark: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e2e4e5",
    backgroundColor: "#ffffff",
    alignItems: "center",
    justifyContent: "center",
  },
  googleG: {
    fontSize: 13,
    fontWeight: "800",
    color: "#4285F4",
  },
  note: {
    marginTop: 18,
    fontSize: 12,
    lineHeight: 19,
    fontWeight: "500",
    color: "#7a7e81",
  },
  footer: {
    marginTop: "auto",
    paddingTop: 42,
    alignItems: "center",
  },
  footerLine: {
    width: 36,
    height: 2,
    borderRadius: 999,
    backgroundColor: "#cfd2d4",
    marginBottom: 14,
  },
  footerText: {
    fontSize: 12,
    lineHeight: 18,
    fontWeight: "800",
    color: "#73777a",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
});
