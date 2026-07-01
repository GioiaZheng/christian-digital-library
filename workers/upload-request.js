const DEFAULT_ALLOWED_ORIGIN = "https://gioiazheng.github.io";
const DEFAULT_MAX_BYTES = 100 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(["zip", "pdf", "epub", "mobi"]);
const PENDING_METADATA_PREFIX = "pending/metadata/";
const PENDING_UPLOAD_PREFIX = "pending/uploads/";
const APPROVED_UPLOAD_PREFIX = "raw/admin-approved/";
const ADMIN_OVERRIDE_PREFIX = "metadata/admin-overrides/";
const ADMIN_READING_STATUS_KEY = "metadata/admin-reading-status.json";
const READING_STATUSES = new Set(["want_to_read", "finished"]);
const READING_STATUS_LABELS = {
  want_to_read: "想读",
  finished: "读完",
};

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowedOrigin = env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN;
  return {
    "Access-Control-Allow-Origin": origin === allowedOrigin ? origin : allowedOrigin,
    "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-CDL-Admin-Code",
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

function cleanRequestId(requestId) {
  const value = cleanText(requestId, 80);
  if (!value || /[/\\]/.test(value)) return "";
  return value;
}

function pendingMetadataKey(requestId) {
  return `${PENDING_METADATA_PREFIX}${cleanRequestId(requestId)}.json`;
}

function requireAdmin(request, env) {
  const expected = String(env.ADMIN_CODE || "").trim();
  const actual = String(request.headers.get("X-CDL-Admin-Code") || "").trim();
  if (!expected) {
    return { ok: false, status: 503, message: "管理员入口尚未配置。" };
  }
  if (actual !== expected) {
    return { ok: false, status: 403, message: "管理员密码不正确。" };
  }
  return { ok: true };
}

async function loadJsonObject(bucket, key) {
  const object = await bucket.get(key);
  if (!object) return null;
  return object.json();
}

async function loadReadingStatuses(env) {
  const stored = await loadJsonObject(env.BOOK_UPLOADS, ADMIN_READING_STATUS_KEY).catch(() => null);
  if (!stored || typeof stored !== "object" || !stored.books || typeof stored.books !== "object") {
    return { books: {} };
  }
  return { books: stored.books };
}

function serializeReadingStatus(bookId, item) {
  const status = String(item?.status || "");
  if (!READING_STATUSES.has(status)) return null;
  return {
    id: bookId,
    status,
    label: READING_STATUS_LABELS[status],
    updated_at: String(item?.updated_at || ""),
  };
}

async function listReadingStatuses(request, env) {
  const stored = await loadReadingStatuses(env);
  const items = Object.entries(stored.books)
    .map(([bookId, item]) => serializeReadingStatus(bookId, item))
    .filter(Boolean)
    .sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
  return jsonResponse(request, env, 200, { items });
}

async function saveReadingStatus(request, env, bookId) {
  if (!/^cdl-\d{6}$/.test(bookId)) {
    return jsonResponse(request, env, 400, { message: "书号不正确。" });
  }

  const body = await request.json().catch(() => ({}));
  const status = cleanText(body.status, 40);
  const now = new Date().toISOString();
  const stored = await loadReadingStatuses(env);

  if (!status || status === "none") {
    delete stored.books[bookId];
  } else if (!READING_STATUSES.has(status)) {
    return jsonResponse(request, env, 400, { message: "阅读状态不正确。" });
  } else {
    stored.books[bookId] = {
      status,
      updated_at: now,
    };
  }

  await env.BOOK_UPLOADS.put(
    ADMIN_READING_STATUS_KEY,
    JSON.stringify({ books: stored.books, updated_at: now }, null, 2),
    {
      httpMetadata: {
        contentType: "application/json; charset=utf-8",
      },
    },
  );

  return jsonResponse(request, env, 200, {
    item: serializeReadingStatus(bookId, stored.books[bookId]) || {
      id: bookId,
      status: "none",
      label: "未标记",
      updated_at: now,
    },
  });
}

async function savePendingMetadata(env, requestId, metadata) {
  await env.BOOK_UPLOADS.put(
    pendingMetadataKey(requestId),
    JSON.stringify(metadata, null, 2),
    {
      httpMetadata: {
        contentType: "application/json; charset=utf-8",
      },
    },
  );
}

async function listPendingUploads(request, env) {
  const listed = await env.BOOK_UPLOADS.list({ prefix: PENDING_METADATA_PREFIX });
  const items = [];
  for (const object of listed.objects) {
    const metadata = await loadJsonObject(env.BOOK_UPLOADS, object.key);
    if (!metadata || metadata.status !== "pending") continue;
    items.push({
      id: metadata.id,
      title: metadata.title,
      author: metadata.author,
      filename: metadata.filename,
      size: metadata.size,
      status: metadata.status,
      submitted_at: metadata.submitted_at,
    });
  }
  items.sort((a, b) => String(b.submitted_at || "").localeCompare(String(a.submitted_at || "")));
  return jsonResponse(request, env, 200, { items });
}

async function updateUploadStatus(request, env, requestId, status) {
  const cleanId = cleanRequestId(requestId);
  if (!cleanId) {
    return jsonResponse(request, env, 400, { message: "提交记录不正确。" });
  }

  const metadata = await loadJsonObject(env.BOOK_UPLOADS, pendingMetadataKey(cleanId));
  if (!metadata) {
    return jsonResponse(request, env, 404, { message: "找不到这条上传申请。" });
  }

  const now = new Date().toISOString();
  metadata.status = status;
  metadata.reviewed_at = now;

  if (status === "approved") {
    const sourceKey = String(metadata.file_key || "");
    const source = await env.BOOK_UPLOADS.get(sourceKey);
    if (!source) {
      return jsonResponse(request, env, 404, { message: "找不到上传文件。" });
    }
    const filename = safeFilename(metadata.filename || sourceKey.split("/").pop());
    const approvedKey = `${APPROVED_UPLOAD_PREFIX}${cleanId}/${filename}`;
    await env.BOOK_UPLOADS.put(approvedKey, source.body, {
      httpMetadata: source.httpMetadata,
      customMetadata: {
        requestId: cleanId,
        title: String(metadata.title || ""),
        author: String(metadata.author || ""),
        status: "approved",
      },
    });
    metadata.approved_file_key = approvedKey;
  }

  await savePendingMetadata(env, cleanId, metadata);
  return jsonResponse(request, env, 200, { item: metadata });
}

async function saveBookOverride(request, env, bookId) {
  if (!/^cdl-\d{6}$/.test(bookId)) {
    return jsonResponse(request, env, 400, { message: "书号不正确。" });
  }
  const body = await request.json().catch(() => ({}));
  const override = {
    id: bookId,
    clean_title: cleanText(body.clean_title, 220),
    author: cleanText(body.author, 160),
    publisher: cleanText(body.publisher, 160),
    year: cleanText(body.year, 40),
    category: cleanText(body.category, 80),
    tags: cleanText(body.tags, 220),
    description: cleanText(body.description, 1200),
    updated_at: new Date().toISOString(),
    status: "admin_override",
  };
  await env.BOOK_UPLOADS.put(
    `${ADMIN_OVERRIDE_PREFIX}${bookId}.json`,
    JSON.stringify(override, null, 2),
    {
      httpMetadata: {
        contentType: "application/json; charset=utf-8",
      },
    },
  );
  return jsonResponse(request, env, 200, { item: override });
}

async function handleAdmin(request, env, pathname) {
  const admin = requireAdmin(request, env);
  if (!admin.ok) {
    return jsonResponse(request, env, admin.status, { message: admin.message });
  }

  if (request.method === "GET" && pathname.endsWith("/admin/uploads")) {
    return listPendingUploads(request, env);
  }

  if (request.method === "GET" && pathname.endsWith("/admin/reading-status")) {
    return listReadingStatuses(request, env);
  }

  const uploadAction = pathname.match(/\/admin\/uploads\/([^/]+)\/(approve|reject)$/);
  if (request.method === "POST" && uploadAction) {
    return updateUploadStatus(
      request,
      env,
      decodeURIComponent(uploadAction[1]),
      uploadAction[2] === "approve" ? "approved" : "rejected",
    );
  }

  const bookUpdate = pathname.match(/\/admin\/books\/(cdl-\d{6})$/);
  if (request.method === "PATCH" && bookUpdate) {
    return saveBookOverride(request, env, bookUpdate[1]);
  }

  const readingStatusUpdate = pathname.match(/\/admin\/books\/(cdl-\d{6})\/reading-status$/);
  if (request.method === "PATCH" && readingStatusUpdate) {
    return saveReadingStatus(request, env, readingStatusUpdate[1]);
  }

  return jsonResponse(request, env, 404, { message: "管理员接口不存在。" });
}

async function handleUpload(request, env) {
  const form = await request.formData().catch(() => null);
  if (!form) {
    return jsonResponse(request, env, 400, { message: "请填写书名、作者并选择文件。" });
  }

  const title = cleanText(form.get("title"), 160);
  const author = cleanText(form.get("author"), 120);
  const file = form.get("file");

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
  const fileKey = `${PENDING_UPLOAD_PREFIX}${requestId}/${filename}`;
  const metadataKey = `${PENDING_METADATA_PREFIX}${requestId}.json`;

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
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    }

    if (!allowedOrigin(request, env)) {
      return jsonResponse(request, env, 403, { message: "来源不允许。" });
    }

    const pathname = new URL(request.url).pathname.replace(/\/+$/, "");
    if (pathname.includes("/admin/")) {
      return handleAdmin(request, env, pathname);
    }

    if (request.method !== "POST") {
      return jsonResponse(request, env, 405, { message: "只接受上传申请。" });
    }

    return handleUpload(request, env);
  },
};
