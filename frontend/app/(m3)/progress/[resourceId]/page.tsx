import Link from "next/link";
import { notFound } from "next/navigation";
import { ResourceProgress } from "../ResourceProgress";

export default async function ProgressPage({ params }: {
  params: Promise<{ resourceId: string }>;
}) {
  const { resourceId } = await params;
  if (!/^[1-9]\d*$/.test(resourceId) || !Number.isSafeInteger(Number(resourceId))) notFound();
  return <main><Link href="/profile">Your profile</Link>
    <ResourceProgress resourceId={Number(resourceId)} />
  </main>;
}
