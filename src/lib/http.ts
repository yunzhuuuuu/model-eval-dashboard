import { NextResponse } from "next/server";

import { ConfigurationError } from "@/lib/db";

export function assertSameOrigin(request: Request): void {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin) {
    throw new Error("CROSS_ORIGIN_REQUEST");
  }
}

export function apiError(error: unknown): NextResponse {
  console.error(error);
  if (error instanceof ConfigurationError) {
    return NextResponse.json({ error: error.message }, { status: 503 });
  }
  if (error instanceof Error) {
    if (error.message === "SESSION_REQUIRED") {
      return NextResponse.json(
        { error: "Your private session expired. Refresh the page to start a new one." },
        { status: 401 },
      );
    }
    if (error.message === "CROSS_ORIGIN_REQUEST") {
      return NextResponse.json({ error: "Request origin was rejected." }, { status: 403 });
    }
  }
  return NextResponse.json(
    { error: "Something went wrong. Please try again." },
    { status: 500 },
  );
}
