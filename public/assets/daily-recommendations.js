(() => {
  const container = document.querySelector("#daily-recommendations");
  const refreshButton = document.querySelector("#daily-refresh");
  if (!container) return;
  let dailyBooks = [];
  let rotation = 0;

  const todayKey = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const hashSeed = (value) => {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  };

  const randomFromSeed = (seed) => {
    let state = seed || 1;
    return () => {
      state = Math.imul(1664525, state) + 1013904223;
      return (state >>> 0) / 4294967296;
    };
  };

  const createText = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  };

  const goodRecommendation = (book) => {
    const title = String(book.clean_title || "").trim();
    if (!title || /^[0-9A-Za-z]{3,}/.test(title)) return false;
    if (/待核|未整理|无标题/.test(title)) return false;
    return true;
  };

  const hasPreviewAssets = (book) =>
    Boolean(String(book.cover_image_url || "").trim()) &&
    Boolean(String(book.preview_base_url || "").trim()) &&
    Number(book.preview_page_count || 0) > 0;

  const canUseReadingFlow = (book) => {
    if (book.reader_ready === false) return false;
    if (book.reader_ready === true || Number(book.reader_page_count || 0) > 0) return true;
    return book.access_required !== false;
  };

  const recommendationRank = (book) => {
    if (!goodRecommendation(book)) return 0;
    if (hasPreviewAssets(book) && canUseReadingFlow(book)) return 3;
    if (hasPreviewAssets(book)) return 2;
    return 1;
  };

  const renderBook = (book) => {
    const article = document.createElement("article");
    article.className = "card";

    const title = document.createElement("h3");
    const link = document.createElement("a");
    link.href = book.detail_url;
    link.textContent = book.clean_title;
    title.append(link);
    article.append(title);

    article.append(
      createText(
        "p",
        "meta",
        [book.author || "作者信息整理中", book.translator ? `译者：${book.translator}` : ""].filter(Boolean).join(" · "),
      ),
    );
    const statusParts = [];
    if (book.cover_image_url) statusParts.push("有封面");
    if (book.preview_base_url && Number(book.preview_page_count || 0) > 0) statusParts.push("可预览");
    statusParts.push(book.preview_base_url ? "可在线阅读" : "阅读版生成中");
    if (book.access_required !== false) statusParts.push("需访问码");
    article.append(createText("p", "card-status", statusParts.join(" · ")));
    const footer = document.createElement("div");
    footer.className = "card-footer";
    footer.append(createText("span", "badge", book.category_name || "馆藏"));
    footer.append(createText("span", "meta", "查看书目 →"));
    article.append(footer);
    return article;
  };

  const pickDailyBooks = (books, offset = 0) => {
    const random = randomFromSeed(hashSeed(`${todayKey()}-${offset}`));
    const picked = [];

    for (const rank of [3, 2, 1]) {
      const pool = books.filter((book) => recommendationRank(book) === rank && !picked.some((item) => item.id === book.id));
      while (pool.length && picked.length < 5) {
        const index = Math.floor(random() * pool.length);
        picked.push(pool.splice(index, 1)[0]);
      }
      if (picked.length >= 5) break;
    }
    return picked;
  };

  const renderPickedBooks = () => {
    const picked = pickDailyBooks(dailyBooks, rotation);
    container.replaceChildren();
    container.setAttribute("aria-busy", "false");
    if (!picked.length) {
      container.append(createText("div", "empty-state", "今日推荐正在整理中，可先进入完整目录。"));
      return;
    }
    picked.forEach((book) => container.append(renderBook(book)));
  };

  const start = async () => {
    try {
      const response = await fetch("catalog.json");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const catalog = await response.json();
      const books = window.CDL_CATALOG_OVERRIDES?.applyToBooks
        ? await window.CDL_CATALOG_OVERRIDES.applyToBooks(catalog)
        : catalog;
      dailyBooks = books;
      renderPickedBooks();
    } catch (error) {
      container.setAttribute("aria-busy", "false");
      const fallback = document.createElement("div");
      fallback.className = "empty-state";
      fallback.append(createText("p", "", "今日推荐暂时加载失败，可先进入完整目录。"));
      const link = document.createElement("a");
      link.href = "catalog.html";
      link.textContent = "进入完整目录 →";
      fallback.append(link);
      container.replaceChildren(fallback);
      console.error(error);
    }
  };

  refreshButton?.addEventListener("click", () => {
    rotation += 1;
    renderPickedBooks();
  });

  start();
})();
