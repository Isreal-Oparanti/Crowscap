import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const BACKEND_URL = (
  process.env.CROWSCAP_BACKEND_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id || !session.user.email) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const proxySecret = process.env.CROWSCAP_PROXY_SECRET;
  if (!proxySecret) {
    return NextResponse.json(
      { detail: "Crowscap authentication is not configured." },
      { status: 500 },
    );
  }

  const response = await fetch(`${BACKEND_URL}/api/v1/notifications/stream`, {
    headers: {
      Accept: "text/event-stream",
      "X-Crowscap-Proxy-Secret": proxySecret,
      "X-Crowscap-User-Id": session.user.id,
      "X-Crowscap-User-Email": session.user.email,
      ...(session.user.name ? { "X-Crowscap-User-Name": session.user.name } : {}),
      ...(session.user.image ? { "X-Crowscap-User-Image": session.user.image } : {}),
    },
    cache: "no-store",
  });

  if (!response.ok || !response.body) {
    return NextResponse.json(
      {
        detail:
          "Crowscap could not open the live notification stream. It will retry when the page refreshes.",
      },
      { status: response.status || 503 },
    );
  }

  return new Response(response.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
