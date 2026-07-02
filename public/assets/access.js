(() => {
  const forms = Array.from(document.querySelectorAll("[data-access-form]"));
  if (!forms.length) return;

  const endpoint = String(window.CDL_ACCESS_ENDPOINT || "").trim();

  const setStatus = (form, message) => {
    const status = form.querySelector("[data-access-status]");
    if (status) status.textContent = message;
  };

  const accessButtons = (form) => Array.from(form.querySelectorAll('button[type="submit"]'));

  const setBusy = (form, busy) => {
    form.dataset.accessBusy = busy ? "true" : "false";
    for (const button of accessButtons(form)) {
      button.disabled = busy;
    }
  };

  const safeExtension = (value) =>
    /^[A-Za-z0-9]+$/.test(String(value || "")) ? String(value).toLowerCase() : "pdf";

  const formatExpiry = (value) => {
    const timestamp = Number(value) * 1000;
    if (!Number.isFinite(timestamp)) return "";
    const date = new Date(timestamp);
    if (!Number.isFinite(date.getTime())) return "";
    return date.toLocaleString("zh-CN", {
      hour12: false,
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
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

  const openReader = (url) => {
    const opened = window.open(url, "_blank");
    if (!opened) {
      throw new Error("浏览器拦截了在线阅读窗口，请允许弹出窗口后重试。");
    }
    opened.opener = null;
  };

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
      const body = new FormData(form);
      body.set("access_action", action);

      setBusy(form, true);
      setStatus(
        form,
        action === "read"
          ? "正在验证访问码并打开在线阅读……"
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

        if (action === "read") {
          const data = await response.json();
          if (!data.reader_url) {
            throw new Error("在线阅读入口暂不可用，请先下载文件。");
          }
          openReader(data.reader_url);
          const expiry = formatExpiry(data.expires_at);
          setStatus(
            form,
            expiry
              ? `访问码已通过，在线阅读已打开。阅读链接有效至 ${expiry}。`
              : "访问码已通过，在线阅读已打开。",
          );
          return;
        }

        const blob = await response.blob();
        const extension = safeExtension(response.headers.get("X-CDL-File-Extension"));
        const fallback = `${form.elements.book_id?.value || "book"}.${extension}`;
        const filename = filenameFromDisposition(
          response.headers.get("Content-Disposition"),
          fallback,
        );
        downloadBlob(blob, filename);
        setStatus(form, "访问码已通过，下载已开始。如果浏览器没有反应，请检查下载权限后重试。");
      } catch (error) {
        setStatus(form, error.message || "访问失败，请稍后再试。");
      } finally {
        setBusy(form, false);
      }
    });
  }
})();
