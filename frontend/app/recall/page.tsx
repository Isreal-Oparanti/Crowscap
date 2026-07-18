import { RecallWorkspace } from "@/components/recall/recall-workspace";
import { SignInScreen } from "@/components/auth/sign-in-screen";
import { authOptions } from "@/lib/auth";
import { getServerSession } from "next-auth";

export default async function RecallPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) return <SignInScreen />;
  const userKey = session.user.id ?? session.user.email ?? "signed-in";
  return <RecallWorkspace key={userKey} user={session.user} />;
}
