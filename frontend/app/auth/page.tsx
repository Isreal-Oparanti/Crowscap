import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { WebSignInForm } from "@/components/auth/web-sign-in-form";

export const metadata = {
  title: "Sign in — Crowscap",
  description: "Sign in to your Crowscap personal memory.",
};

export default async function AuthPage({
  searchParams,
}: {
  searchParams?: Promise<{ mode?: string }>;
}) {
  const session = await getServerSession(authOptions);
  if (session?.user) redirect("/");
  const resolvedParams = await searchParams;
  const initialMode = resolvedParams?.mode === "signup" ? "signup" : "login";
  return <WebSignInForm initialMode={initialMode} />;
}

