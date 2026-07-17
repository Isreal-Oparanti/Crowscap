import { RecallWorkspace } from "@/components/recall/recall-workspace";
import { SignInScreen } from "@/components/auth/sign-in-screen";
import { authOptions } from "@/lib/auth";
import { getServerSession } from "next-auth";

export default async function RecallMemoryPage({
  params,
}: {
  params: Promise<{ memoryId: string }>;
}) {
  const session = await getServerSession(authOptions);
  if (!session?.user) return <SignInScreen />;
  const { memoryId } = await params;
  return <RecallWorkspace requestedMemoryId={memoryId} user={session.user} />;
}
