(() => {
  const form = document.querySelector("#upload-request-form");
  const status = document.querySelector("#upload-request-status");
  if (!form || !status) return;

  const endpoint =
    String(window.CDL_UPLOAD_ENDPOINT || "").trim() ||
    String(form.dataset.uploadEndpoint || "").trim();
  const submit = form.querySelector('button[type="submit"]');
  const allowedExtensions = new Set(["pdf", "epub", "mobi"]);

  const setStatus = (message) => {
    status.textContent = message;
  };

  const extensionOf = (filename) => {
    const match = /\.([A-Za-z0-9]+)$/.exec(String(filename || ""));
    return match ? match[1].toLowerCase() : "";
  };

  if (!endpoint) {
    if (submit) submit.disabled = true;
    setStatus("上传入口正在接入中。");
    return;
  }

  setStatus("填写后可提交，资料会先进入待审核区。");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!submit) return;

    const file = form.file?.files?.[0];
    if (!file) {
      setStatus("请选择要上传的文件。");
      return;
    }
    if (!allowedExtensions.has(extensionOf(file.name))) {
      setStatus("请上传 PDF、EPUB 或 MOBI 文件，不要上传 ZIP。");
      return;
    }
    const maxBytes = Number(form.dataset.maxBytes || 104857600);
    if (Number.isFinite(maxBytes) && maxBytes > 0 && file.size > maxBytes) {
      const maxMb = Math.floor(maxBytes / 1024 / 1024);
      setStatus(`文件太大，单个文件最大 ${maxMb} MB。`);
      return;
    }

    submit.disabled = true;
    setStatus("正在提交，请不要关闭页面。");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        body: new FormData(form),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || "提交失败，请稍后再试。");
      }
      form.reset();
      setStatus("已提交，等待审核。");
    } catch (error) {
      setStatus(error.message || "提交失败，请稍后再试。");
    } finally {
      submit.disabled = false;
    }
  });
})();
