import { getServerSession } from "next-auth";

import { SignInScreen } from "@/components/auth/sign-in-screen";
import { SettingsWorkspace } from "@/components/settings/settings-workspace";
import { authOptions } from "@/lib/auth";

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) return <SignInScreen isLoggedIn={false} />;

  return <SettingsWorkspace user={session.user} />;
}
