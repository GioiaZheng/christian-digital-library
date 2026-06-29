(() => {
  const forms = Array.from(document.querySelectorAll("[data-access-form]"));
  if (!forms.length) return;

  const endpoint = String(window.CDL_ACCESS_ENDPOINT || "").trim();
  const openedUrls = [];

  const READABLE_TYPES = new Map([
    ["pdf", "application/pdf"],
    ["html", "text/html;charset=utf-8"],
    ["htm", "text/html;charset=utf-8"],
    ["txt", "text/plain;charset=utf-8"],
    ["md", "text/plain;charset=utf-8"],
    ["jpg", "image/jpeg"],
    ["jpeg", "image/jpeg"],
    ["png", "image/png"],
    ["gif", "image/gif"],
    ["webp", "image/webp"],
  ]);

  const ZIP_SIGNATURE_END_OF_CENTRAL_DIRECTORY = 0x06054b50;
  const ZIP_SIGNATURE_CENTRAL_DIRECTORY = 0x02014b50;
  const ZIP_SIGNATURE_LOCAL_FILE = 0x04034b50;

  const setStatus = (form, message) => {
    const status = form.querySelector("[data-access-status]");
    if (status) status.textContent = message;
  };

  const escapeHtml = (value) =>
    String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const accessButtons = (form) => Array.from(form.querySelectorAll('button[type="submit"]'));

  const setBusy = (form, busy) => {
    for (const button of accessButtons(form)) {
      button.disabled = busy;
    }
  };

  const filenameFromDisposition = (value, fallback) => {
    const encoded = /filename\*=UTF-8''([^;]+)/i.exec(value || "");
    if (encoded) {
      try {
        return decodeURIComponent(encoded[1]);
      } catch (_error) {
        return fallback;
      }
    }
    const plain = /filename="([^"]+)"/i.exec(value || "");
    return plain ? plain[1] : fallback;
  };

  const extensionFromName = (filename) => {
    const match = /\.([A-Za-z0-9]+)$/.exec(filename || "");
    return match ? match[1].toLowerCase() : "";
  };

  const isZipFile = (filename, type) => {
    const extension = extensionFromName(filename);
    return extension === "zip" || /zip/i.test(type || "");
  };

  const readUint16 = (bytes, offset) => bytes[offset] | (bytes[offset + 1] << 8);

  const readUint32 = (bytes, offset) =>
    (bytes[offset] |
      (bytes[offset + 1] << 8) |
      (bytes[offset + 2] << 16) |
      (bytes[offset + 3] << 24)) >>> 0;

  const decodeZipName = (bytes, useUtf8) => {
    const encodings = useUtf8 ? ["utf-8"] : ["gb18030", "gbk", "utf-8"];
    for (const encoding of encodings) {
      try {
        return new TextDecoder(encoding).decode(bytes);
      } catch (_error) {
        // Try the next browser-supported encoding.
      }
    }
    return Array.from(bytes, (byte) => String.fromCharCode(byte)).join("");
  };

  const findEndOfCentralDirectory = (bytes) => {
    const minOffset = Math.max(0, bytes.length - 66000);
    for (let offset = bytes.length - 22; offset >= minOffset; offset -= 1) {
      if (readUint32(bytes, offset) === ZIP_SIGNATURE_END_OF_CENTRAL_DIRECTORY) {
        return offset;
      }
    }
    throw new Error("这个 ZIP 文件暂时无法在线解析，请先下载后打开。");
  };

  const parseZipEntries = (bytes) => {
    const eocdOffset = findEndOfCentralDirectory(bytes);
    const entryCount = readUint16(bytes, eocdOffset + 10);
    const centralDirectorySize = readUint32(bytes, eocdOffset + 12);
    const centralDirectoryOffset = readUint32(bytes, eocdOffset + 16);

    if (
      entryCount === 0xffff ||
      centralDirectorySize === 0xffffffff ||
      centralDirectoryOffset === 0xffffffff
    ) {
      throw new Error("这个 ZIP 使用了 ZIP64 格式，当前网页暂不支持在线解析，请先下载后打开。");
    }

    const entries = [];
    let offset = centralDirectoryOffset;
    const end = centralDirectoryOffset + centralDirectorySize;

    while (offset < end && entries.length < entryCount) {
      if (readUint32(bytes, offset) !== ZIP_SIGNATURE_CENTRAL_DIRECTORY) {
        throw new Error("这个 ZIP 的目录结构暂时无法在线解析，请先下载后打开。");
      }

      const flags = readUint16(bytes, offset + 8);
      const method = readUint16(bytes, offset + 10);
      const compressedSize = readUint32(bytes, offset + 20);
      const uncompressedSize = readUint32(bytes, offset + 24);
      const nameLength = readUint16(bytes, offset + 28);
      const extraLength = readUint16(bytes, offset + 30);
      const commentLength = readUint16(bytes, offset + 32);
      const localHeaderOffset = readUint32(bytes, offset + 42);
      const nameBytes = bytes.slice(offset + 46, offset + 46 + nameLength);
      const name = decodeZipName(nameBytes, Boolean(flags & 0x0800));

      if (!name.endsWith("/")) {
        entries.push({
          name,
          method,
          compressedSize,
          uncompressedSize,
          localHeaderOffset,
        });
      }

      offset += 46 + nameLength + extraLength + commentLength;
    }

    return entries;
  };

  const readablePriority = (entry) => {
    const extension = extensionFromName(entry.name);
    const priority = Array.from(READABLE_TYPES.keys()).indexOf(extension);
    return priority === -1 ? Number.POSITIVE_INFINITY : priority;
  };

  const chooseReadableEntry = (entries) =>
    entries
      .filter((entry) => READABLE_TYPES.has(extensionFromName(entry.name)))
      .sort((left, right) => {
        const priorityDiff = readablePriority(left) - readablePriority(right);
        if (priorityDiff !== 0) return priorityDiff;
        return right.uncompressedSize - left.uncompressedSize;
      })[0];

  const inflateRaw = async (blob) => {
    if (typeof DecompressionStream === "undefined") {
      throw new Error("当前浏览器暂不支持在线解压 ZIP，请先下载后打开。");
    }

    const stream = blob.stream().pipeThrough(new DecompressionStream("deflate-raw"));
    return new Response(stream).arrayBuffer();
  };

  const extractZipEntry = async (bytes, entry) => {
    const offset = entry.localHeaderOffset;
    if (readUint32(bytes, offset) !== ZIP_SIGNATURE_LOCAL_FILE) {
      throw new Error("这个 ZIP 的文件内容暂时无法在线解析，请先下载后打开。");
    }

    const nameLength = readUint16(bytes, offset + 26);
    const extraLength = readUint16(bytes, offset + 28);
    const dataStart = offset + 30 + nameLength + extraLength;
    const dataEnd = dataStart + entry.compressedSize;
    const compressedBlob = new Blob([bytes.slice(dataStart, dataEnd)]);

    if (entry.method === 0) {
      return compressedBlob.arrayBuffer();
    }
    if (entry.method === 8) {
      return inflateRaw(compressedBlob);
    }

    throw new Error("这个 ZIP 使用了网页暂不支持的压缩方式，请先下载后打开。");
  };

  const openReaderBlob = (readerWindow, blob, filename) => {
    const url = URL.createObjectURL(blob);
    openedUrls.push(url);

    if (readerWindow && !readerWindow.closed) {
      readerWindow.location.href = url;
      return;
    }

    const opened = window.open(url, "_blank");
    if (!opened) {
      throw new Error("浏览器拦截了在线阅读窗口，请允许弹出窗口后重试。");
    }
  };

  const writeReaderMessage = (readerWindow, message) => {
    if (!readerWindow || readerWindow.closed) return;
    readerWindow.document.title = "在线阅读";
    readerWindow.document.body.innerHTML = `
      <main style="font-family: sans-serif; max-width: 720px; margin: 48px auto; line-height: 1.8;">
        <h1 style="font-size: 24px;">在线阅读</h1>
        <p>${escapeHtml(message)}</p>
      </main>
    `;
  };

  const openReadableFile = async (blob, filename, readerWindow) => {
    if (!isZipFile(filename, blob.type)) {
      const extension = extensionFromName(filename);
      const type = READABLE_TYPES.get(extension) || blob.type || "application/octet-stream";
      openReaderBlob(readerWindow, blob.slice(0, blob.size, type), filename);
      return filename;
    }

    const bytes = new Uint8Array(await blob.arrayBuffer());
    const entries = parseZipEntries(bytes);
    const entry = chooseReadableEntry(entries);
    if (!entry) {
      throw new Error("这个 ZIP 里暂时没有找到可直接在线阅读的 PDF、文本或图片，请先下载。");
    }

    const extension = extensionFromName(entry.name);
    const type = READABLE_TYPES.get(extension) || "application/octet-stream";
    const content = await extractZipEntry(bytes, entry);
    const readerBlob = new Blob([content], { type });
    openReaderBlob(readerWindow, readerBlob, entry.name);
    return entry.name;
  };

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  window.addEventListener("beforeunload", () => {
    for (const url of openedUrls) {
      URL.revokeObjectURL(url);
    }
  });

  for (const form of forms) {
    if (!endpoint) {
      setBusy(form, true);
      setStatus(form, "访问入口正在接入中。");
      continue;
    }

    setStatus(form, "输入访问码后可在线阅读或下载文件。");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const action = event.submitter?.value === "read" ? "read" : "download";
      const readerWindow = action === "read" ? window.open("", "_blank") : null;
      if (action === "read" && !readerWindow) {
        setStatus(form, "浏览器拦截了在线阅读窗口，请允许弹出窗口后重试。");
        return;
      }
      if (readerWindow) {
        writeReaderMessage(readerWindow, "正在验证访问码并准备内容……");
      }

      const body = new FormData(form);
      body.set("access_action", action);

      setBusy(form, true);
      setStatus(
        form,
        action === "read"
          ? "正在验证访问码并准备在线阅读……"
          : "正在验证访问码并准备下载……",
      );

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          body,
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.message || "访问失败，请稍后再试。");
        }

        const blob = await response.blob();
        const fallback = `${form.elements.book_id?.value || "book"}.zip`;
        const filename = filenameFromDisposition(
          response.headers.get("Content-Disposition"),
          fallback,
        );

        if (action === "read") {
          const openedName = await openReadableFile(blob, filename, readerWindow);
          setStatus(form, `已打开在线阅读：${openedName}`);
        } else {
          downloadBlob(blob, filename);
          setStatus(form, "访问码已通过，下载已开始。");
        }
      } catch (error) {
        if (readerWindow && !readerWindow.closed) {
          writeReaderMessage(readerWindow, error.message || "在线阅读失败。");
        }
        setStatus(form, error.message || "访问失败，请稍后再试。");
      } finally {
        setBusy(form, false);
      }
    });
  }
})();
