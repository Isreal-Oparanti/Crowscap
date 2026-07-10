import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = (
  process.env.CROWSCAP_BACKEND_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
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
      },
      body,
      cache: "no-store",
    });
    const responseBody = await response.text();

    return new NextResponse(responseBody, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
      },
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
