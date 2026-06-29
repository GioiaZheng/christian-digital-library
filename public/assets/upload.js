(() => {
  const form = document.querySelector("#upload-request-form");
  const status = document.querySelector("#upload-request-status");
  if (!form || !status) return;

  const endpoint =
    String(window.CDL_UPLOAD_ENDPOINT || "").trim() ||
    String(form.dataset.uploadEndpoint || "").trim();
  const submit = form.querySelector('button[type="submit"]');

  const setStatus = (message) => {
    status.textContent = message;
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
