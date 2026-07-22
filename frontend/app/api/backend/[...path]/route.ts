import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";

const BACKEND_URL = (
  process.env.CROWSCAP_BACKEND_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const isAdminRoute = path[0] === "admin";

  const session = await getServerSession(authOptions);
  if (!isAdminRoute && (!session?.user?.id || !session.user.email)) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const proxySecret = process.env.CROWSCAP_PROXY_SECRET;
  if (!proxySecret) {
    return NextResponse.json(
      { detail: "Crowscap authentication is not configured." },
      { status: 500 },
    );
  }

  const target = new URL(
    `${BACKEND_URL}/api/v1/${path.join("/")}${request.nextUrl.search}`,
  );

  try {
    const body =
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer();
    const contentType = request.headers.get("content-type");
    const response = await fetch(target, {
      method: request.method,
      headers: {
        Accept: "application/json",
        ...(body && contentType ? { "Content-Type": contentType } : {}),
        "X-Crowscap-Proxy-Secret": proxySecret,
        ...(request.headers.get("cookie") ? { "Cookie": request.headers.get("cookie")! } : {}),
        ...(session?.user?.id ? { "X-Crowscap-User-Id": session.user.id } : {}),
        ...(session?.user?.email ? { "X-Crowscap-User-Email": session.user.email } : {}),
        ...(session?.user?.name ? { "X-Crowscap-User-Name": session.user.name } : {}),
        ...(session?.user?.image ? { "X-Crowscap-User-Image": session.user.image } : {}),
      },
      body,
      cache: "no-store",
    });
    const responseBody = await response.text();
    const responseContentType =
      response.headers.get("content-type") ?? "application/json";

    if (!responseContentType.includes("application/json")) {
      const trimmed = responseBody.trim();
      const detail =
        trimmed && !trimmed.startsWith("<")
          ? trimmed
          : response.ok
            ? "Crowscap returned an unexpected non-JSON response."
            : "Crowscap backend returned an unexpected error.";
      return NextResponse.json({ detail }, { status: response.status });
    }

    const responseHeaders = new Headers();
    responseHeaders.set("Content-Type", responseContentType);
    
    const setCookies = response.headers.getSetCookie ? response.headers.getSetCookie() : [];
    if (setCookies.length > 0) {
      for (const cookie of setCookies) {
        responseHeaders.append("Set-Cookie", cookie);
      }
    } else {
      const setCookieStr = response.headers.get("set-cookie");
      if (setCookieStr) {
        responseHeaders.set("Set-Cookie", setCookieStr);
      }
    }

    return new NextResponse(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Crowscap could not reach the local memory service. Start the FastAPI backend and try again.",
      },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
