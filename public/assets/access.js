(() => {
  const forms = Array.from(document.querySelectorAll("[data-access-form]"));
  if (!forms.length) return;

  const endpoint = String(window.CDL_ACCESS_ENDPOINT || "").trim();

  const setStatus = (form, message) => {
    const status = form.querySelector("[data-access-status]");
    if (status) status.textContent = message;
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

  for (const form of forms) {
    const submit = form.querySelector('button[type="submit"]');
    if (!endpoint) {
      if (submit) submit.disabled = true;
      setStatus(form, "访问入口正在接入中。");
      continue;
    }

    setStatus(form, "输入访问码后可下载文件。");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!submit) return;

      submit.disabled = true;
      setStatus(form, "正在验证访问码……");

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          body: new FormData(form),
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
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        setStatus(form, "访问码已通过，下载已开始。");
      } catch (error) {
        setStatus(form, error.message || "访问失败，请稍后再试。");
      } finally {
        submit.disabled = false;
      }
    });
  }
})();
