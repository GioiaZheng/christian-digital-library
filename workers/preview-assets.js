const ALLOWED_ASSET_PATTERNS = [
  /^covers\/cdl-\d+\.jpg$/,
  /^previews\/cdl-\d+\/page-[1-9]\d*\.jpg$/,
];

const SECURITY_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Cross-Origin-Resource-Policy": "cross-origin",
  "X-Content-Type-Options": "nosniff",
};

function responseHeaders(object) {
  const headers = new Headers(SECURITY_HEADERS);
  headers.set("Cache-Control", "public, max-age=86400");
  headers.set("Content-Type", object.httpMetadata?.contentType || "image/jpeg");
  return headers;
}

function notFound() {
  return new Response("Not Found", {
    status: 404,
    headers: SECURITY_HEADERS,
  });
}

function allowedKey(pathname) {
  const key = decodeURIComponent(pathname.replace(/^\/+/, ""));
  if (!ALLOWED_ASSET_PATTERNS.some((pattern) => pattern.test(key))) {
    return "";
  }
  return key;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: SECURITY_HEADERS });
    }
    if (!["GET", "HEAD"].includes(request.method)) {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: SECURITY_HEADERS,
      });
    }

    const key = allowedKey(url.pathname);
    if (!key) return notFound();

    const object = await env.BOOK_ASSETS.get(key);
    if (!object) return notFound();

    if (request.method === "HEAD") {
      return new Response(null, {
        status: 200,
        headers: responseHeaders(object),
      });
    }

    return new Response(object.body, {
      status: 200,
      headers: responseHeaders(object),
    });
  },
};
