(() => {
  const input = document.querySelector("#category-search-input");
  const results = document.querySelector("#category-results");
  const summary = document.querySelector("#category-result-summary");
  const emptyState = document.querySelector("#category-empty-state");

  if (!input || !results || !summary || !emptyState) return;

  const cards = Array.from(results.querySelectorAll(".card"));
  const total = Number(results.dataset.categoryTotal || cards.length);
  const normalize = (value) => String(value || "").trim().toLocaleLowerCase("zh-CN");

  const updateCard = (card, override) => {
    if (!override) return;
    const title = card.querySelector("[data-card-title]");
    const byline = card.querySelector("[data-card-byline]");
    const description = card.querySelector("[data-card-description]");
    const category = card.querySelector("[data-card-category]");
    if (title && override.clean_title) title.textContent = override.clean_title;
    if (byline) byline.textContent = [override.author || "作者待核", override.year].filter(Boolean).join(" · ");
    if (description && override.description) description.textContent = override.description;
    if (category && (override.category_name || override.category)) {
      category.textContent = override.category_name || override.category;
    }
    card.dataset.filterText = [
      override.clean_title,
      override.author,
      override.publisher,
      override.description,
      override.category_name,
      ...(override.tags || []),
    ]
      .filter(Boolean)
      .join(" ");
  };

  const applyLiveOverrides = async () => {
    if (!window.CDL_CATALOG_OVERRIDES?.getBookOverride) return;
    await Promise.all(
      cards.map(async (card) => {
        const bookId = card.dataset.catalogBookId;
        if (!bookId) return;
        updateCard(card, await window.CDL_CATALOG_OVERRIDES.getBookOverride(bookId));
      }),
    );
  };

  const setQueryString = () => {
    const params = new URLSearchParams(location.search);
    const value = input.value.trim();
    if (value) {
      params.set("q", value);
    } else {
      params.delete("q");
    }
    const query = params.toString();
    history.replaceState(null, "", query ? `?${query}` : location.pathname);
  };

  const render = () => {
    const words = normalize(input.value).split(/\s+/).filter(Boolean);
    let visible = 0;

    cards.forEach((card) => {
      const haystack = normalize(card.dataset.filterText || card.textContent);
      const matched = words.every((word) => haystack.includes(word));
      card.hidden = !matched;
      if (matched) visible += 1;
    });

    if (words.length) {
      summary.textContent = `共 ${total} 条书目，筛选出 ${visible} 条`;
    } else {
      summary.textContent = `共 ${total} 条书目`;
    }
    emptyState.hidden = visible !== 0;
    setQueryString();
  };

  const setupAndRender = () => {
    const params = new URLSearchParams(location.search);
    input.value = params.get("q") || "";
    input.addEventListener("input", render);
    if (!cards.length) {
      input.disabled = true;
      emptyState.hidden = true;
      return;
    }
    render();
  };

  const start = async () => {
    await applyLiveOverrides();
    setupAndRender();
  };

  start().catch((error) => {
    console.warn("分类页实时书目资料暂时无法读取。", error);
    setupAndRender();
  });
})();
