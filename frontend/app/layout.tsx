import "./globals.css";

import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Crowscap AI",
  description: "A second brain that remembers, questions, and recalls what you learn.",
  applicationName: "Crowscap AI",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icons/crowscap-icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/crowscap-icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  appleWebApp: {
    capable: true,
    title: "Crowscap AI",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#111111",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
