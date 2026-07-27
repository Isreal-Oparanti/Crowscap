import { Stack } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/context";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
    },
  },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="sign-in" />
          <Stack.Screen name="(tabs)" />
          <Stack.Screen
            name="(modals)/capture"
            options={{ presentation: "modal" }}
          />
          <Stack.Screen
            name="(modals)/capture-result"
            options={{ presentation: "modal" }}
          />
          <Stack.Screen
            name="(modals)/memory/[id]"
            options={{ presentation: "modal" }}
          />
        </Stack>
      </AuthProvider>
    </QueryClientProvider>
  );
}
