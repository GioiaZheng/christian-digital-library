(() => {
  const endpoint = String(window.CDL_ACCESS_ENDPOINT || "").trim();
  const params = new URLSearchParams(window.location.search);
  const bookId = params.get("book") || "";
  const token = params.get("token") || "";

  const title = document.querySelector("[data-reader-title]");
  const status = document.querySelector("[data-reader-status]");
  const pages = document.querySelector("[data-reader-pages]");
  const toolbar = document.querySelector("[data-reader-toolbar]");
  const detailLink = document.querySelector("[data-reader-detail]");
  const backButton = document.querySelector("[data-reader-back]");
  const jumpForm = document.querySelector("[data-reader-jump]");
  const pageInput = document.querySelector("[data-reader-page-input]");
  const pageTotal = document.querySelector("[data-reader-page-total]");
  const prevPageButton = document.querySelector("[data-reader-prev]");
  const nextPageButton = document.querySelector("[data-reader-next]");
  const zoomOutButton = document.querySelector("[data-reader-zoom-out]");
  const zoomResetButton = document.querySelector("[data-reader-zoom-reset]");
  const zoomInButton = document.querySelector("[data-reader-zoom-in]");
  let currentPage = 1;
  let currentPageTotal = 0;
  let readerScale = 1;

  const setStatus = (message) => {
    if (status) status.textContent = message;
  };

  const paddedPage = (index) => String(index).padStart(4, "0");

  const pageId = (index) => `page-${index}`;

  const readerUrl = (filename) => {
    const url = new URL(`${endpoint.replace(/\/+$/, "")}/reader/${bookId}/${filename}`);
    url.searchParams.set("token", token);
    return url.toString();
  };

  const validBookId = /^cdl-\d{6}$/.test(bookId);

  const applyReaderZoom = () => {
    if (pages) pages.style.setProperty("--reader-zoom", String(readerScale));
    if (zoomResetButton) zoomResetButton.textContent = `${Math.round(readerScale * 100)}%`;
    if (zoomOutButton) zoomOutButton.disabled = readerScale <= 0.7;
    if (zoomInButton) zoomInButton.disabled = readerScale >= 2;
  };

  const zoomReader = (step) => {
    readerScale = Math.min(2, Math.max(0.7, Number((readerScale + step).toFixed(2))));
    applyReaderZoom();
  };

  const resetReaderZoom = () => {
    readerScale = 1;
    applyReaderZoom();
  };

  const updateCurrentPage = (pageNumber, pageCount = currentPageTotal) => {
    const total = Number(pageCount) || 0;
    const safePage = total
      ? Math.min(Math.max(Number(pageNumber) || 1, 1), total)
      : Math.max(Number(pageNumber) || 1, 1);
    currentPage = safePage;
    currentPageTotal = total;
    if (pageInput) pageInput.value = String(safePage);
    if (prevPageButton) prevPageButton.disabled = safePage <= 1;
    if (nextPageButton) nextPageButton.disabled = total ? safePage >= total : true;
  };

  if (detailLink && validBookId) {
    detailLink.href = `books/${bookId}.html`;
  }

  if (backButton) {
    backButton.addEventListener("click", () => {
      if (window.history.length > 1) {
        window.history.back();
        return;
      }
      window.location.href = validBookId ? `books/${bookId}.html` : "index.html";
    });
  }

  const scrollToPage = (pageNumber, pageCount) => {
    const safePage = Math.min(Math.max(Number(pageNumber) || 1, 1), pageCount);
    const target = document.getElementById(pageId(safePage));
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    updateCurrentPage(safePage, pageCount);
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}${window.location.search}#${pageId(safePage)}`,
    );
  };

  const watchCurrentPage = () => {
    if (!pageInput || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        const pageNumber = visible?.target?.dataset?.page;
        if (pageNumber) updateCurrentPage(pageNumber);
      },
      {
        rootMargin: "-38% 0px -52% 0px",
        threshold: [0, 0.1, 0.25],
      },
    );
    pages.querySelectorAll(".reader-page").forEach((page) => observer.observe(page));
  };

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

    if (toolbar) toolbar.hidden = false;
    if (pageInput) {
      pageInput.max = String(pageCount);
    }
    updateCurrentPage(1, pageCount);
    if (pageTotal) pageTotal.textContent = `共 ${pageCount} 页`;
    if (jumpForm) {
      jumpForm.addEventListener("submit", (event) => {
        event.preventDefault();
        scrollToPage(pageInput?.value, pageCount);
      });
    }
    if (prevPageButton) {
      prevPageButton.addEventListener("click", () => {
        scrollToPage(currentPage - 1, pageCount);
      });
    }
    if (nextPageButton) {
      nextPageButton.addEventListener("click", () => {
        scrollToPage(currentPage + 1, pageCount);
      });
    }
    zoomOutButton?.addEventListener("click", () => zoomReader(-0.15));
    zoomResetButton?.addEventListener("click", resetReaderZoom);
    zoomInButton?.addEventListener("click", () => zoomReader(0.15));
    applyReaderZoom();

    const fragment = document.createDocumentFragment();
    for (let index = 1; index <= pageCount; index += 1) {
      const figure = document.createElement("figure");
      figure.className = "reader-page";
      figure.id = pageId(index);
      figure.dataset.page = String(index);

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
    watchCurrentPage();

    const hashPage = /^#page-(\d+)$/.exec(window.location.hash || "");
    if (hashPage) {
      window.setTimeout(() => scrollToPage(hashPage[1], pageCount), 0);
    }
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
