import { getStore } from "@netlify/blobs";
import { createHash, randomUUID } from "node:crypto";

const STORE = "muzetr-comments";
const MAX_NAME = 24;
const MAX_BODY = 800;
const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const PER_IP_PER_DAY = 20;

const ALLOWED_IMAGE = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
  "image/gif": "gif",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function hashIp(ip) {
  return createHash("sha256").update(ip + "|muzetr").digest("hex").slice(0, 16);
}

// 用路径的哈希做 key，避免 %2F 这类编码在不同环节被解码导致读写不一致
function hashPath(path) {
  return createHash("sha1").update(path).digest("hex").slice(0, 20);
}

function decodeImage(dataUrl) {
  if (typeof dataUrl !== "string" || !dataUrl.startsWith("data:")) return null;
  const match = /^data:([^;]+);base64,(.+)$/s.exec(dataUrl);
  if (!match) return null;
  const mime = match[1].toLowerCase();
  if (!ALLOWED_IMAGE[mime]) return { error: "unsupported-image" };
  let bytes;
  try {
    bytes = Uint8Array.from(Buffer.from(match[2], "base64"));
  } catch {
    return { error: "bad-image" };
  }
  if (bytes.byteLength > MAX_IMAGE_BYTES) return { error: "image-too-large" };
  return { mime, bytes, ext: ALLOWED_IMAGE[mime] };
}

export default async function handler(request) {
  const store = getStore({ name: STORE, consistency: "strong" });
  const url = new URL(request.url);
  const pagePath = (url.searchParams.get("path") || "").slice(0, 200);

  if (request.method === "GET") {
    // 管理员：列出全部评论（含所属文章）
    if (url.searchParams.get("admin") === "1") {
      const token = request.headers.get("x-admin-token");
      if (!process.env.ADMIN_TOKEN || token !== process.env.ADMIN_TOKEN) {
        return json({ error: "forbidden" }, 403);
      }
      const { blobs } = await store.list({ prefix: "c/" });
      const all = await Promise.all(
        blobs.slice(-500).map((blob) => store.get(blob.key, { type: "json" }).catch(() => null))
      );
      return json({
        total: all.filter(Boolean).length,
        comments: all.filter(Boolean).map(({ ipHash, ...rest }) => rest),
      });
    }
    if (!pagePath) return json({ comments: [] });
    const prefix = `c/${hashPath(pagePath)}/`;
    const { blobs } = await store.list({ prefix });
    const loaded = await Promise.all(
      blobs.slice(-300).map((blob) => store.get(blob.key, { type: "json" }).catch(() => null))
    );
    const comments = loaded
      .filter((item) => item && !item.hidden)
      .map(({ ipHash, ...rest }) => rest)
      .sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));
    return json({ comments });
  }

  if (request.method !== "POST") return json({ error: "method" }, 405);

  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ error: "bad-json" }, 400);
  }

  if (payload.website) return json({ ok: true, spam: true });

  // 管理员操作：删除单条（payload.id）或清空（payload.path 可选，省略则清空全部）
  if (payload.action === "delete" || payload.action === "purge") {
    const adminToken = process.env.ADMIN_TOKEN;
    if (!adminToken || request.headers.get("x-admin-token") !== adminToken) {
      return json({ error: "forbidden" }, 403);
    }

    if (payload.action === "delete") {
      const id = String(payload.id || "");
      if (!id) return json({ error: "empty" }, 400);
      const { blobs } = await store.list({ prefix: "c/" });
      let removed = 0;
      for (const blob of blobs) {
        if (blob.key.includes(id)) {
          await store.delete(blob.key);
          removed += 1;
        }
      }
      return json({ ok: true, removed });
    }

    const scope = String(payload.path || "").slice(0, 200);
    const prefix = scope ? `c/${hashPath(scope)}/` : "c/";
    const { blobs } = await store.list({ prefix });
    let removed = 0;
    for (const blob of blobs) {
      await store.delete(blob.key);
      removed += 1;
    }
    return json({ ok: true, removed });
  }

  const name = String(payload.name || "").trim().slice(0, MAX_NAME);
  const body = String(payload.body || "").trim().slice(0, MAX_BODY);
  const target = String(payload.path || "").slice(0, 200);
  if (!name || !body || !target) return json({ error: "empty" }, 400);
  if (body.length < 2) return json({ error: "too-short" }, 400);

  const ip =
    request.headers.get("x-nf-client-connection-ip") ||
    (request.headers.get("x-forwarded-for") || "").split(",")[0].trim();
  const ipHash = hashIp(ip || "unknown");

  const day = new Date().toISOString().slice(0, 10);
  const rateKey = `rl/${ipHash}/${day}`;
  const used = (await store.get(rateKey, { type: "text" }).catch(() => null)) || "0";
  const count = Number.parseInt(used, 10) || 0;
  if (count >= PER_IP_PER_DAY) return json({ error: "rate-limited" }, 429);

  let imageUrl = null;
  if (payload.image) {
    const decoded = decodeImage(payload.image);
    if (!decoded) return json({ error: "bad-image" }, 400);
    if (decoded.error) return json({ error: decoded.error }, 400);
    const key = `img/${randomUUID()}.${decoded.ext}`;
    await store.set(key, decoded.bytes, { metadata: { contentType: decoded.mime } });
    imageUrl = `/api/image/${key.split("/")[1]}`;
  }

  const id = randomUUID();
  const createdAt = Date.now();
  const comment = { id, name, body, image: imageUrl, createdAt };
  await store.setJSON(`c/${hashPath(target)}/${String(createdAt).padStart(14, "0")}-${id}.json`, {
    ...comment,
    page: target,
    ipHash,
  });
  await store.set(rateKey, String(count + 1));
  return json({ ok: true, comment });
}

export const config = { path: "/api/comments" };
