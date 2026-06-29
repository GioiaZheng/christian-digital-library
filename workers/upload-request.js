const DEFAULT_ALLOWED_ORIGIN = "https://gioiazheng.github.io";
const DEFAULT_MAX_BYTES = 100 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(["zip", "pdf", "epub", "mobi"]);

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowedOrigin = env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN;
  return {
    "Access-Control-Allow-Origin": origin === allowedOrigin ? origin : allowedOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
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

function safeFilename(name) {
  const cleaned = String(name || "upload")
    .normalize("NFKC")
    .replace(/[<>:"/\\|?*\u0000-\u001f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || "upload";
}

function extensionOf(filename) {
  const match = /\.([A-Za-z0-9]+)$/.exec(filename);
  return match ? match[1].toLowerCase() : "";
}

function allowedOrigin(request, env) {
  const origin = request.headers.get("Origin");
  return !origin || origin === (env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN);
}

function validUploadCode(form, env) {
  const expected = String(env.UPLOAD_CODE || "").trim();
  const actual = cleanText(form.get("upload_code"), 120);
  if (!expected) {
    return { ok: false, status: 503, message: "上传入口尚未配置提交码。" };
  }
  if (actual !== expected) {
    return { ok: false, status: 403, message: "提交码不正确。" };
  }
  return { ok: true };
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
      return jsonResponse(request, env, 405, { message: "只接受上传申请。" });
    }

    const form = await request.formData();
    const title = cleanText(form.get("title"), 160);
    const author = cleanText(form.get("author"), 120);
    const file = form.get("file");
    const codeCheck = validUploadCode(form, env);

    if (!codeCheck.ok) {
      return jsonResponse(request, env, codeCheck.status, { message: codeCheck.message });
    }

    if (!title || !author || !(file instanceof File)) {
      return jsonResponse(request, env, 400, { message: "请填写书名、作者并选择文件。" });
    }

    const filename = safeFilename(file.name);
    const extension = extensionOf(filename);
    if (!ALLOWED_EXTENSIONS.has(extension)) {
      return jsonResponse(request, env, 400, { message: "文件格式暂不支持。" });
    }

    const maxBytes = Number(env.MAX_UPLOAD_BYTES || DEFAULT_MAX_BYTES);
    if (file.size > maxBytes) {
      return jsonResponse(request, env, 413, { message: "文件太大，请联系管理员处理。" });
    }

    const requestId = crypto.randomUUID();
    const now = new Date().toISOString();
    const fileKey = `pending/uploads/${requestId}/${filename}`;
    const metadataKey = `pending/metadata/${requestId}.json`;

    await env.BOOK_UPLOADS.put(fileKey, file.stream(), {
      httpMetadata: {
        contentType: file.type || "application/octet-stream",
      },
      customMetadata: {
        requestId,
        title,
        author,
        status: "pending",
      },
    });

    await env.BOOK_UPLOADS.put(
      metadataKey,
      JSON.stringify(
        {
          id: requestId,
          title,
          author,
          filename,
          file_key: fileKey,
          size: file.size,
          content_type: file.type || "",
          status: "pending",
          submitted_at: now,
        },
        null,
        2,
      ),
      {
        httpMetadata: {
          contentType: "application/json; charset=utf-8",
        },
      },
    );

    return jsonResponse(request, env, 202, {
      id: requestId,
      message: "已提交，等待审核。",
    });
  },
};
