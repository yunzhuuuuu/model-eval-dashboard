import { upload } from "@vercel/blob/client";

const baseUrl = new URL(
  process.argv[2] ?? "https://model-eval-dashboard-black.vercel.app",
);
const origin = baseUrl.origin;
const uploadedUrls = [];
let cookie = "";

function assertOk(response, label) {
  if (!response.ok) {
    return response.text().then((body) => {
      throw new Error(`${label} failed (${response.status}): ${body}`);
    });
  }
  return response;
}

async function cleanup() {
  if (!cookie || uploadedUrls.length === 0) return;
  await fetch(new URL("/api/uploads", baseUrl), {
    method: "DELETE",
    headers: {
      "content-type": "application/json",
      cookie,
      origin,
    },
    body: JSON.stringify({ urls: uploadedUrls }),
  });
}

try {
  const sessionResponse = await assertOk(
    await fetch(new URL("/api/session", baseUrl), {
      method: "POST",
      headers: { origin },
    }),
    "Session creation",
  );
  cookie = sessionResponse.headers.get("set-cookie")?.split(";", 1)[0] ?? "";
  if (!cookie) throw new Error("Session response did not set a cookie.");
  const session = await sessionResponse.json();

  const requestHeaders = { cookie, origin };
  const contextCsv = [
    "Note",
    '"The library closes at nine on weekdays."',
    '"The community garden meeting is Saturday morning."',
    '"Blueberries should be refrigerated after washing."',
  ].join("\n");
  const qandaCsv = [
    "Question,Relevant Note",
    '"When does the library close during the week?","The library closes at nine on weekdays."',
    '"When is the garden group meeting?","The community garden meeting is Saturday morning."',
  ].join("\n");

  const contextBlob = await upload(
    `${session.id}/uploads/${crypto.randomUUID()}-context.csv`,
    contextCsv,
    {
      access: "private",
      contentType: "text/csv",
      handleUploadUrl: new URL("/api/uploads", baseUrl).toString(),
      clientPayload: JSON.stringify({ role: "context" }),
      headers: requestHeaders,
    },
  );
  uploadedUrls.push(contextBlob.url);

  const qandaBlob = await upload(
    `${session.id}/uploads/${crypto.randomUUID()}-qanda.csv`,
    qandaCsv,
    {
      access: "private",
      contentType: "text/csv",
      handleUploadUrl: new URL("/api/uploads", baseUrl).toString(),
      clientPayload: JSON.stringify({ role: "qanda" }),
      headers: requestHeaders,
    },
  );
  uploadedUrls.push(qandaBlob.url);

  const enqueueResponse = await assertOk(
    await fetch(new URL("/api/datasets", baseUrl), {
      method: "POST",
      headers: { ...requestHeaders, "content-type": "application/json" },
      body: JSON.stringify({
        name: `Production smoke ${new Date().toISOString()}`,
        contextBlobUrl: contextBlob.url,
        qandaBlobUrl: qandaBlob.url,
      }),
    }),
    "Evaluation enqueue",
  );

  console.log(JSON.stringify({ session, ...(await enqueueResponse.json()) }));
} catch (error) {
  await cleanup();
  throw error;
}
