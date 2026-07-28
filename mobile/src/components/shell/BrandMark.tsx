import { Image, StyleSheet, View } from "react-native";
import { tokens } from "@/theme/tokens";

const logo = require("../../../assets/icon.png");

interface BrandMarkProps {
  size?: number;
  imageSize?: number;
}

export function BrandMark({ size = 40, imageSize = 30 }: BrandMarkProps) {
  return (
    <View
      style={[
        styles.frame,
        {
          width: size,
          height: size,
          borderRadius: Math.round(size * 0.28),
        },
      ]}
    >
      <Image
        source={logo}
        style={{ width: imageSize, height: imageSize }}
        resizeMode="contain"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.colors.surface,
    borderWidth: 1,
    borderColor: tokens.colors.border,
  },
});
