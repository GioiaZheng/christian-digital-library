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
    const bookTitle = manifest.title || bookId;

    if (title) title.textContent = bookTitle;
    if (!Number.isFinite(pageCount) || pageCount <= 0) {
      setStatus("阅读页正在生成，请稍后再试。");
      return;
    }

    const fragment = document.createDocumentFragment();
    for (let index = 1; index <= pageCount; index += 1) {
      const figure = document.createElement("figure");
      figure.className = "reader-page";
      figure.id = `page-${index}`;

      const imageUrl = readerUrl(`page-${paddedPage(index)}.${extension}`);
      const image = document.createElement("img");
      image.loading = index <= 2 ? "eager" : "lazy";
      image.decoding = "async";
      image.src = imageUrl;
      image.alt = `${bookTitle} 第 ${index} 页`;

      const errorBox = document.createElement("div");
      errorBox.className = "reader-page-error";
      errorBox.hidden = true;

      const errorText = document.createElement("p");
      errorText.textContent = `第 ${index} 页加载失败。`;

      const retryButton = document.createElement("button");
      retryButton.className = "button secondary";
      retryButton.type = "button";
      retryButton.textContent = "重试本页";

      retryButton.addEventListener("click", () => {
        const retryUrl = new URL(imageUrl);
        retryUrl.searchParams.set("retry", String(Date.now()));
        figure.classList.remove("is-error");
        errorBox.hidden = true;
        image.hidden = false;
        image.src = retryUrl.toString();
        setStatus(`正在重新加载第 ${index} 页……`);
      });

      image.addEventListener("load", () => {
        figure.classList.remove("is-error");
        errorBox.hidden = true;
        image.hidden = false;
      });

      image.addEventListener("error", () => {
        figure.classList.add("is-error");
        image.hidden = true;
        errorBox.hidden = false;
        setStatus(`第 ${index} 页加载失败，可以点“重试本页”。`);
      });

      errorBox.append(errorText, retryButton);

      const caption = document.createElement("figcaption");
      caption.textContent = `第 ${index} / ${pageCount} 页`;

      figure.append(image, errorBox, caption);
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
