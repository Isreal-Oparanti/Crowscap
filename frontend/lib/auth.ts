import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

function normalizeUserId(value: string | null | undefined): string {
  const safe = (value ?? "user")
    .replace(/[^a-zA-Z0-9_.:-]/g, "")
    .slice(0, 34);
  return `g_${safe || "user"}`;
}

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET ?? process.env.AUTH_SECRET,
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/",
  },
  providers: [
    GoogleProvider({
      clientId: process.env.AUTH_GOOGLE_ID ?? process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret:
        process.env.AUTH_GOOGLE_SECRET ?? process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
    CredentialsProvider({
      name: "Demo Account",
      credentials: {
        email: { label: "Email", type: "text" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (credentials?.email === "yc@crowscap.xyz" && credentials?.password === "demo2026") {
          return { id: "demo_yc_user", name: "YC Reviewer", email: "yc@crowscap.xyz" };
        }
        return null;
      }
    })
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.provider === "google") {
        token.crowscapUserId = normalizeUserId(account.providerAccountId);
      } else if (!token.crowscapUserId) {
        token.crowscapUserId = normalizeUserId(token.sub ?? token.email);
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = String(
          token.crowscapUserId ?? normalizeUserId(token.sub ?? token.email),
        );
      }
      return session;
    },
  },
};
