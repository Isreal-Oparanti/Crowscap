import { View } from "react-native";
import { Tabs } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Icons } from "@/components/ui/Icon";
import { useRecalls } from "@/hooks/useRecalls";
import { tokens } from "@/theme/tokens";
import { fontFamily } from "@/theme/typography";

export default function TabLayout() {
  const insets = useSafeAreaInsets();
  const bottomInset = Math.max(insets.bottom + 6, 18);
  const { data: recallData } = useRecalls();
  const hasUnreadRecalls = (recallData?.memories?.length ?? 0) > 0;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: tokens.colors.text,
        tabBarInactiveTintColor: "#888b8e",
        tabBarStyle: {
          backgroundColor: "#ffffff",
          borderTopColor: "#f0f1f3",
          borderTopWidth: 1,
          height: 54 + bottomInset,
          paddingBottom: bottomInset,
          paddingTop: 6,
          paddingHorizontal: 28,
          shadowColor: "#000000",
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.03,
          shadowRadius: 8,
          elevation: 4,
        },

        tabBarItemStyle: {
          paddingHorizontal: 8,
        },
        tabBarLabelStyle: {
          fontSize: 10,
          fontFamily: fontFamily.bold,
          letterSpacing: 0,
          marginTop: 1,
        },
        tabBarIconStyle: {
          marginTop: 1,
        },
      }}

    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Chat",
          tabBarIcon: ({ color, focused }) => (
            <Icons.MessageCircle
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
            <View style={{ position: "relative" }}>
              <Icons.BookOpenCheck
                size={20}
                color={color}
                style={{ opacity: focused ? 1 : 0.75 }}
              />
              {hasUnreadRecalls ? (
                <View
                  style={{
                    position: "absolute",
                    top: 4.3,
                    right: -7,
                    width: 9,
                    height: 9,
                    borderRadius: 5,
                    borderWidth: 1.5,
                    borderColor: "#ffffff",
                    backgroundColor: "#2d7058",
                  }}
                />
              ) : null}
            </View>




          ),
        }}
      />

      <Tabs.Screen
        name="search"
        options={{
          title: "Search",
          tabBarIcon: ({ color, focused }) => (
            <Icons.Search
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
