import "server-only";

import {
  createHash,
  createHmac,
  randomBytes,
  randomUUID,
  timingSafeEqual,
} from "node:crypto";
import { cookies } from "next/headers";

import { ConfigurationError, database } from "@/lib/db";

const COOKIE_NAME = "model_eval_session";
const SESSION_DAYS = 7;
const SESSION_SECONDS = SESSION_DAYS * 24 * 60 * 60;

export type PrivateSession = {
  id: string;
  expiresAt: Date;
};

function secret(): string {
  const value = process.env.SESSION_SECRET;
  if (!value || value.length < 32) {
    throw new ConfigurationError(
      "SESSION_SECRET must be configured with at least 32 random characters.",
    );
  }
  return value;
}

function signature(payload: string): string {
  return createHmac("sha256", secret()).update(payload).digest("base64url");
}

function tokenHash(token: string): Buffer {
  return createHash("sha256").update(token).digest();
}

function safeEqual(left: string, right: string): boolean {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

async function readCookie(): Promise<{ id: string; token: string } | null> {
  const value = (await cookies()).get(COOKIE_NAME)?.value;
  if (!value) return null;
  const [id, token, suppliedSignature, ...extra] = value.split(".");
  if (!id || !token || !suppliedSignature || extra.length > 0) return null;
  if (!safeEqual(signature(`${id}.${token}`), suppliedSignature)) return null;
  return { id, token };
}

export async function requireSession(): Promise<PrivateSession> {
  const parsed = await readCookie();
  if (!parsed) throw new Error("SESSION_REQUIRED");

  const sql = database();
  const rows = await sql<{ id: string; expires_at: Date }[]>`
    UPDATE app_sessions
    SET last_seen_at = now()
    WHERE id = ${parsed.id}
      AND token_hash = ${tokenHash(parsed.token)}
      AND expires_at > now()
    RETURNING id, expires_at
  `;
  const row = rows[0];
  if (!row) throw new Error("SESSION_REQUIRED");
  return { id: row.id, expiresAt: new Date(row.expires_at) };
}

export async function ensureSession(): Promise<PrivateSession> {
  try {
    return await requireSession();
  } catch (error) {
    if (!(error instanceof Error) || error.message !== "SESSION_REQUIRED") {
      throw error;
    }
  }

  const id = randomUUID();
  const token = randomBytes(32).toString("base64url");
  const expiresAt = new Date(Date.now() + SESSION_SECONDS * 1000);
  const sql = database();
  await sql`
    INSERT INTO app_sessions (id, token_hash, expires_at)
    VALUES (${id}, ${tokenHash(token)}, ${expiresAt})
  `;

  const payload = `${id}.${token}`;
  (await cookies()).set(COOKIE_NAME, `${payload}.${signature(payload)}`, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_SECONDS,
    priority: "high",
  });
  return { id, expiresAt };
}
