(() => {
  const endpoint = String(window.CDL_ACCESS_ENDPOINT || "").trim();
  const params = new URLSearchParams(window.location.search);
  const bookId = params.get("book") || "";
  const token = params.get("token") || "";

  const title = document.querySelector("[data-reader-title]");
  const status = document.querySelector("[data-reader-status]");
  const pages = document.querySelector("[data-reader-pages]");

  const setStatus = (message) => {
    if (status) status.textContent = message;
  };

  const paddedPage = (index) => String(index).padStart(4, "0");

  const readerUrl = (filename) => {
    const url = new URL(`${endpoint.replace(/\/+$/, "")}/reader/${bookId}/${filename}`);
    url.searchParams.set("token", token);
    return url.toString();
  };

  const validBookId = /^cdl-\d{6}$/.test(bookId);

  if (!endpoint || !validBookId || !token) {
    setStatus("阅读链接不完整，请回到书目页重新输入访问码。");
    return;
  }

  const renderPages = (manifest) => {
    const pageCount = Number(manifest.page_count || 0);
    const extension = String(manifest.page_extension || "webp").replace(/[^A-Za-z0-9]/g, "") || "webp";

    if (title) title.textContent = manifest.title || bookId;
    if (!Number.isFinite(pageCount) || pageCount <= 0) {
      setStatus("阅读页正在生成，请稍后再试。");
      return;
    }

    const fragment = document.createDocumentFragment();
    for (let index = 1; index <= pageCount; index += 1) {
      const figure = document.createElement("figure");
      figure.className = "reader-page";
      figure.id = `page-${index}`;

      const image = document.createElement("img");
      image.loading = index <= 2 ? "eager" : "lazy";
      image.decoding = "async";
      image.src = readerUrl(`page-${paddedPage(index)}.${extension}`);
      image.alt = `${manifest.title || bookId} 第 ${index} 页`;

      const caption = document.createElement("figcaption");
      caption.textContent = `第 ${index} / ${pageCount} 页`;

      figure.append(image, caption);
      fragment.append(figure);
    }

    pages.replaceChildren(fragment);
    setStatus(`共 ${pageCount} 页。向下滑动阅读。`);
  };

  const loadManifest = async () => {
    try {
      const response = await fetch(readerUrl("manifest.json"), {
        headers: { Accept: "application/json" },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || "阅读权限已过期，请重新输入访问码。");
      }
      renderPages(data);
    } catch (error) {
      setStatus(error.message || "在线阅读暂不可用，请稍后再试。");
    }
  };

  loadManifest();
})();
