const DEFAULT_ALLOWED_ORIGIN = "https://gioiazheng.github.io";
const DEFAULT_ACCESS_MAP_KEY = "metadata/access-map.json";
const BOOK_ID_PATTERN = /^cdl-\d{6}$/;
const ALLOWED_FILE_EXTENSIONS = new Set(["zip", "pdf", "epub", "mobi"]);

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowedOrigin = env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN;
  return {
    "Access-Control-Allow-Origin": origin === allowedOrigin ? origin : allowedOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Expose-Headers": "Content-Disposition",
    "X-Content-Type-Options": "nosniff",
  };
}

function jsonResponse(request, env, status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...corsHeaders(request, env),
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}

function cleanText(value, maxLength) {
  return String(value || "").trim().replace(/\s+/g, " ").slice(0, maxLength);
}

function allowedOrigin(request, env) {
  const origin = request.headers.get("Origin");
  return !origin || origin === (env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN);
}

function extensionOf(filename) {
  const match = /\.([A-Za-z0-9]+)$/.exec(filename);
  return match ? match[1].toLowerCase() : "";
}

function safeDownloadName(value, fallback) {
  const cleaned = String(value || fallback || "book")
    .normalize("NFKC")
    .replace(/[<>:"/\\|?*\u0000-\u001f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || fallback || "book";
}

function encodedDispositionFilename(filename, fallbackName) {
  const extension = extensionOf(filename);
  const fallbackBase = String(fallbackName || "book")
    .replace(/[^\x20-\x7e]+/g, "_")
    .replace(/["\\/:;]+/g, "")
    .trim() || "book";
  const fallback = extension && !fallbackBase.toLowerCase().endsWith(`.${extension}`)
    ? `${fallbackBase}.${extension}`
    : fallbackBase;
  const encoded = encodeURIComponent(filename).replace(/[!'()*]/g, (character) =>
    `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
  );
  return `attachment; filename="${fallback}"; filename*=UTF-8''${encoded}`;
}

function validAccessCode(form, env) {
  const expected = String(env.ACCESS_CODE || "").trim();
  const actual = cleanText(form.get("access_code"), 120);
  if (!expected) {
    return { ok: false, status: 503, message: "访问入口尚未配置访问码。" };
  }
  if (actual !== expected) {
    return { ok: false, status: 403, message: "访问码不正确。" };
  }
  return { ok: true };
}

async function loadAccessMap(env) {
  const key = env.ACCESS_MAP_KEY || DEFAULT_ACCESS_MAP_KEY;
  const object = await env.BOOK_FILES.get(key);
  if (!object) {
    throw new Error("访问映射尚未生成。");
  }
  return object.json();
}

function bookRecord(accessMap, bookId) {
  if (accessMap && accessMap.books && accessMap.books[bookId]) {
    return accessMap.books[bookId];
  }
  return null;
}

function validObjectKey(key) {
  const value = String(key || "");
  const extension = extensionOf(value);
  return value.startsWith("raw/") && ALLOWED_FILE_EXTENSIONS.has(extension);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    }

    if (!allowedOrigin(request, env)) {
      return jsonResponse(request, env, 403, { message: "来源不允许。" });
    }

    if (request.method !== "POST") {
      return jsonResponse(request, env, 405, { message: "只接受访问请求。" });
    }

    const form = await request.formData();
    const bookId = cleanText(form.get("book_id"), 32);
    const codeCheck = validAccessCode(form, env);

    if (!BOOK_ID_PATTERN.test(bookId)) {
      return jsonResponse(request, env, 400, { message: "书目编号不正确。" });
    }
    if (!codeCheck.ok) {
      return jsonResponse(request, env, codeCheck.status, { message: codeCheck.message });
    }

    let accessMap;
    try {
      accessMap = await loadAccessMap(env);
    } catch (error) {
      return jsonResponse(request, env, 503, { message: error.message || "访问映射读取失败。" });
    }

    const record = bookRecord(accessMap, bookId);
    if (!record || !validObjectKey(record.key)) {
      return jsonResponse(request, env, 404, { message: "此书目暂未接入下载文件。" });
    }

    const object = await env.BOOK_FILES.get(record.key);
    if (!object) {
      return jsonResponse(request, env, 404, { message: "文件暂不可用。" });
    }

    const extension = extensionOf(record.key) || "zip";
    const filename = `${safeDownloadName(record.title, bookId)}.${extension}`;
    const headers = new Headers(corsHeaders(request, env));
    headers.set("Cache-Control", "private, max-age=0, no-store");
    headers.set("Content-Disposition", encodedDispositionFilename(filename, bookId));
    headers.set("Content-Type", object.httpMetadata?.contentType || "application/octet-stream");
    if (object.size) {
      headers.set("Content-Length", String(object.size));
    }

    return new Response(object.body, {
      status: 200,
      headers,
    });
  },
};
