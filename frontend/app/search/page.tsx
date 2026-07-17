import { SearchWorkspace } from "@/components/search/search-workspace";
import { SignInScreen } from "@/components/auth/sign-in-screen";
import { authOptions } from "@/lib/auth";
import { getServerSession } from "next-auth";

export default async function SearchPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) return <SignInScreen />;
  return <SearchWorkspace user={session.user} />;
}
