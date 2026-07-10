import { RecallWorkspace } from "@/components/recall/recall-workspace";

export default async function RecallMemoryPage({
  params,
}: {
  params: Promise<{ memoryId: string }>;
}) {
  const { memoryId } = await params;
  return <RecallWorkspace requestedMemoryId={memoryId} />;
}
