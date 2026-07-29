import { Tabs } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { Platform } from "react-native";
import { tokens } from "@/theme/tokens";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: tokens.colors.text,
        tabBarInactiveTintColor: "#888b8e",
        tabBarStyle: {
          backgroundColor: "rgba(255,255,255,0.97)",
          borderTopColor: "#e2e4e5",
          borderTopWidth: 1,
          height: Platform.OS === "ios" ? 84 : 64,
          paddingBottom: Platform.OS === "ios" ? 28 : 10,
          paddingTop: 10,
          shadowColor: "#111111",
          shadowOffset: { width: 0, height: -4 },
          shadowOpacity: 0.04,
          shadowRadius: 12,
          elevation: 10,
        },
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: "700",
          letterSpacing: 0.1,
          marginTop: 2,
        },
        tabBarIconStyle: {
          marginTop: 2,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Chat",
          tabBarIcon: ({ color, focused }) => (
            <Feather
              name="message-circle"
              size={20}
              color={color}
              style={{ opacity: focused ? 1 : 0.75 }}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="recall"
        options={{
          title: "Recall",
          tabBarIcon: ({ color, focused }) => (
            <Feather
              name="book-open"
              size={20}
              color={color}
              style={{ opacity: focused ? 1 : 0.75 }}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: "Search",
          tabBarIcon: ({ color, focused }) => (
            <Feather
              name="search"
              size={20}
              color={color}
              style={{ opacity: focused ? 1 : 0.75 }}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}
