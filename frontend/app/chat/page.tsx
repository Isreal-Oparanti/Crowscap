import { ChatWorkspace } from "@/components/chat/chat-workspace";
import { SignInScreen } from "@/components/auth/sign-in-screen";
import { authOptions } from "@/lib/auth";
import { getServerSession } from "next-auth";

export default async function ChatPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) return <SignInScreen isLoggedIn={false} />;
  const userKey = session.user.id ?? session.user.email ?? "signed-in";
  return <ChatWorkspace key={userKey} user={session.user} />;
}
