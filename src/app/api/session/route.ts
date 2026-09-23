import { NextResponse } from "next/server";

import { apiError, assertSameOrigin } from "@/lib/http";
import { ensureSession } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<NextResponse> {
  try {
    assertSameOrigin(request);
    const session = await ensureSession();
    return NextResponse.json({
      id: session.id,
      expiresAt: session.expiresAt.toISOString(),
    });
  } catch (error) {
    return apiError(error);
  }
}
