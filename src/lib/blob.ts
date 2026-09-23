import "server-only";

const PRIVATE_BLOB_HOST = /^[a-z0-9-]+\.private\.blob\.vercel-storage\.com$/i;

export function validateOwnedBlobUrl(urlValue: string, sessionId: string): URL {
  let url: URL;
  try {
    url = new URL(urlValue);
  } catch {
    throw new Error("INVALID_BLOB_URL");
  }
  if (
    url.protocol !== "https:" ||
    !PRIVATE_BLOB_HOST.test(url.hostname) ||
    !url.pathname.startsWith(`/${sessionId}/`)
  ) {
    throw new Error("INVALID_BLOB_URL");
  }
  return url;
}
