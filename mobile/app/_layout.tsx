import { Stack, useRouter, useSegments } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import * as Updates from "expo-updates";
import {
  Manrope_400Regular,
  Manrope_500Medium,
  Manrope_600SemiBold,
  Manrope_700Bold,
  Manrope_800ExtraBold,
  useFonts,
} from "@expo-google-fonts/manrope";
import { AuthProvider } from "@/auth/context";
import { useAuth } from "@/hooks/useAuth";
import { useNotifications } from "@/hooks/useNotifications";
import { ShareIntentHandler } from "@/components/capture/ShareIntentHandler";
import { AppUpdatePrompt } from "@/components/shell/AppUpdatePrompt";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
      gcTime: 5 * 60_000,
    },
  },
});

/**
 * Silently checks for an OTA update on startup and reloads the app immediately
 * if one is found. Runs in the background — user never has to tap anything.
 * Works regardless of the checkAutomatically native config in the APK binary.
 */
async function silentlyApplyOtaUpdate() {
  if (__DEV__) return;
  try {
    const check = await Updates.checkForUpdateAsync();
    if (!check.isAvailable) return;
    await Updates.fetchUpdateAsync();
    await Updates.reloadAsync();
  } catch {
    // Silently fail — don't interrupt the user experience
  }
}

function AuthGate() {
  const { session, isLoading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  // Enable push notifications when user is logged in
  useNotifications(Boolean(session));

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === "sign-in";

    if (!session && !inAuthGroup) {
      router.replace("/sign-in");
    } else if (session && inAuthGroup) {
      router.replace("/(tabs)" as any);
    }
  }, [session, isLoading, segments, router]);

  return null;
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Manrope_400Regular,
    Manrope_500Medium,
    Manrope_600SemiBold,
    Manrope_700Bold,
    Manrope_800ExtraBold,
  });

  useEffect(() => {
    // Run silent OTA update check on every cold start
    silentlyApplyOtaUpdate();
  }, []);

  if (!fontsLoaded) {
    return null;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AuthGate />
        <ShareIntentHandler />
        <AppUpdatePrompt />
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, animation: "fade" }}>
          <Stack.Screen
            name="sign-in"
            options={{ contentStyle: { backgroundColor: "#0d0e11" } }}
          />

          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="settings" />
          <Stack.Screen
            name="(modals)/capture"
            options={{
              presentation: "modal",
              animation: "slide_from_bottom",
            }}
          />
          <Stack.Screen
            name="(modals)/capture-result"
            options={{
              presentation: "modal",
              animation: "slide_from_bottom",
            }}
          />
          <Stack.Screen
            name="(modals)/memory/[id]"
            options={{
              presentation: "modal",
              animation: "slide_from_bottom",
            }}
          />
        </Stack>
      </AuthProvider>
    </QueryClientProvider>
  );
}
