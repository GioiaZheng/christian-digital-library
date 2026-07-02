const DEFAULT_ALLOWED_ORIGIN = "https://gioiazheng.github.io";
const DEFAULT_ACCESS_MAP_KEY = "metadata/access-map.json";
const DEFAULT_READER_PAGE_URL = "https://gioiazheng.github.io/christian-digital-library/reader.html";
const DEFAULT_READER_TOKEN_TTL_SECONDS = 4 * 60 * 60;
const BOOK_ID_PATTERN = /^cdl-\d{6}$/;
const READER_PATH_PATTERN = /^\/reader\/(cdl-\d{6})\/(manifest\.json|page-\d{4}\.(?:webp|jpg|jpeg|png))$/;
const ALLOWED_FILE_EXTENSIONS = new Set(["zip", "pdf", "epub", "mobi"]);
const ALLOWED_ACCESS_ACTIONS = new Set(["download", "read"]);

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowedOrigin = env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN;
  return {
    "Access-Control-Allow-Origin": origin === allowedOrigin ? origin : allowedOrigin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Expose-Headers": "Content-Disposition, X-CDL-File-Extension",
    "X-Content-Type-Options": "nosniff",
  };
}

function jsonResponse(request, env, status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...corsHeaders(request, env),
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
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

function encodedDispositionFilename(filename, fallbackName, disposition = "attachment") {
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
  return `${disposition}; filename="${fallback}"; filename*=UTF-8''${encoded}`;
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

function accessAction(form) {
  const action = cleanText(form.get("access_action"), 20) || "download";
  return ALLOWED_ACCESS_ACTIONS.has(action) ? action : "";
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

function readerManifestKey(bookId) {
  return `reader/${bookId}/manifest.json`;
}

function readerObjectKey(bookId, filename) {
  return `reader/${bookId}/${filename}`;
}

function readerTokenTtl(env) {
  const value = Number(env.READER_TOKEN_TTL_SECONDS || DEFAULT_READER_TOKEN_TTL_SECONDS);
  if (!Number.isFinite(value) || value < 300) return DEFAULT_READER_TOKEN_TTL_SECONDS;
  return Math.min(value, 24 * 60 * 60);
}

function readerSecret(env) {
  return String(env.READER_TOKEN_SECRET || env.ACCESS_CODE || "").trim();
}

function base64UrlEncode(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function signReaderPayload(payload, env) {
  const secret = readerSecret(env);
  if (!secret) throw new Error("阅读入口尚未配置访问密钥。");
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  return base64UrlEncode(signature);
}

function safeEqual(left, right) {
  const a = String(left || "");
  const b = String(right || "");
  let mismatch = a.length === b.length ? 0 : 1;
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    mismatch |= (a.charCodeAt(index) || 0) ^ (b.charCodeAt(index) || 0);
  }
  return mismatch === 0;
}

async function createReaderToken(bookId, env) {
  const expiresAt = Math.floor(Date.now() / 1000) + readerTokenTtl(env);
  const payload = `${bookId}.${expiresAt}`;
  const signature = await signReaderPayload(payload, env);
  return {
    token: `${payload}.${signature}`,
    expiresAt,
  };
}

async function validateReaderToken(bookId, token, env) {
  const parts = String(token || "").split(".");
  if (parts.length !== 3) return false;

  const [tokenBookId, expiresAtText, signature] = parts;
  if (tokenBookId !== bookId || !BOOK_ID_PATTERN.test(tokenBookId)) return false;

  const expiresAt = Number(expiresAtText);
  if (!Number.isFinite(expiresAt) || expiresAt < Math.floor(Date.now() / 1000)) {
    return false;
  }

  const expected = await signReaderPayload(`${tokenBookId}.${expiresAtText}`, env);
  return safeEqual(expected, signature);
}

function readerUrl(bookId, token, env) {
  const url = new URL(env.READER_PAGE_URL || DEFAULT_READER_PAGE_URL);
  url.searchParams.set("book", bookId);
  url.searchParams.set("token", token);
  return url.toString();
}

function normalizedManifest(manifest, bookId, title) {
  const pageCount = Number(manifest?.page_count || manifest?.pages?.length || 0);
  return {
    book_id: bookId,
    title: String(manifest?.title || title || bookId),
    page_count: Number.isFinite(pageCount) && pageCount > 0 ? Math.floor(pageCount) : 0,
    page_extension: String(manifest?.page_extension || "webp").replace(/[^A-Za-z0-9]/g, "") || "webp",
  };
}

async function handleReaderRequest(request, env, url) {
  const match = url.pathname.match(READER_PATH_PATTERN);
  if (!match) {
    return jsonResponse(request, env, 404, { message: "阅读资源不存在。" });
  }

  const [, bookId, filename] = match;
  const token = url.searchParams.get("token") || "";
  if (!(await validateReaderToken(bookId, token, env))) {
    return jsonResponse(request, env, 403, { message: "阅读访问已过期，请重新输入访问码。" });
  }

  const key = readerObjectKey(bookId, filename);
  const object = await env.BOOK_FILES.get(key);
  if (!object) {
    return jsonResponse(request, env, 404, { message: "阅读资源正在生成。" });
  }

  if (filename === "manifest.json") {
    const manifest = await object.json();
    return jsonResponse(request, env, 200, normalizedManifest(manifest, bookId, manifest?.title));
  }

  const headers = new Headers(corsHeaders(request, env));
  headers.set("Cache-Control", "private, max-age=600");
  headers.set("Content-Type", object.httpMetadata?.contentType || "image/webp");
  if (object.size) headers.set("Content-Length", String(object.size));

  if (request.method === "HEAD") {
    return new Response(null, { status: 200, headers });
  }
  return new Response(object.body, { status: 200, headers });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    }

    if (!allowedOrigin(request, env)) {
      return jsonResponse(request, env, 403, { message: "来源不允许。" });
    }

    if (request.method === "GET" || request.method === "HEAD") {
      return handleReaderRequest(request, env, url);
    }

    if (request.method !== "POST") {
      return jsonResponse(request, env, 405, { message: "只接受访问请求。" });
    }

    const form = await request.formData();
    const bookId = cleanText(form.get("book_id"), 32);
    const action = accessAction(form);
    const codeCheck = validAccessCode(form, env);

    if (!BOOK_ID_PATTERN.test(bookId)) {
      return jsonResponse(request, env, 400, { message: "书目编号不正确。" });
    }
    if (!action) {
      return jsonResponse(request, env, 400, { message: "访问动作不正确。" });
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

    if (action === "read") {
      const manifestObject = await env.BOOK_FILES.get(readerManifestKey(bookId));
      if (!manifestObject) {
        return jsonResponse(request, env, 404, {
          message: "此书的在线阅读版正在生成，请先下载文件。",
        });
      }
      const manifest = await manifestObject.json();
      const readerToken = await createReaderToken(bookId, env);
      return jsonResponse(request, env, 200, {
        reader_url: readerUrl(bookId, readerToken.token, env),
        expires_at: readerToken.expiresAt,
        ...normalizedManifest(manifest, bookId, record.title),
      });
    }

    const object = await env.BOOK_FILES.get(record.key);
    if (!object) {
      return jsonResponse(request, env, 404, { message: "文件暂不可用。" });
    }

    const extension = extensionOf(record.key) || "pdf";
    const filename = `${safeDownloadName(record.title, bookId)}.${extension}`;
    const headers = new Headers(corsHeaders(request, env));
    headers.set("Cache-Control", "private, max-age=0, no-store");
    headers.set("Content-Disposition", encodedDispositionFilename(filename, bookId));
    headers.set("Content-Type", object.httpMetadata?.contentType || "application/octet-stream");
    headers.set("X-CDL-File-Extension", extension);
    if (object.size) {
      headers.set("Content-Length", String(object.size));
    }

    return new Response(object.body, {
      status: 200,
      headers,
    });
  },
};
