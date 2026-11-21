import { getStore } from "@netlify/blobs";

const STORE = "muzetr-comments";

export default async function handler(request) {
  const url = new URL(request.url);
  const fileName = decodeURIComponent(url.pathname.replace(/^\/api\/image\//, ""));
  if (!fileName || fileName.includes("/") || fileName.includes("..")) {
    return new Response("not found", { status: 404 });
  }

  const store = getStore({ name: STORE, consistency: "strong" });
  const result = await store
    .getWithMetadata(`img/${fileName}`, { type: "arrayBuffer" })
    .catch(() => null);

  if (!result) return new Response("not found", { status: 404 });

  return new Response(result.data, {
    headers: {
      "content-type": result.metadata?.contentType || "image/jpeg",
      "cache-control": "public, max-age=31536000, immutable",
    },
  });
}

export const config = { path: "/api/image/*" };
