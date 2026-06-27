(() => {
  const searchInput = document.querySelector("#search-input");
  const categorySelect = document.querySelector("#category-filter");
  const results = document.querySelector("#search-results");
  const summary = document.querySelector("#result-summary");

  if (!searchInput || !categorySelect || !results || !summary) return;

  const normalize = (value) => String(value || "").trim().toLocaleLowerCase("zh-CN");

  const createText = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
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

    const bylineParts = [book.author || "作者待核", book.year].filter(Boolean);
    article.append(createText("p", "meta", bylineParts.join(" · ")));
    article.append(createText("p", "description", book.description || "暂无内容简介。"));

    const footer = document.createElement("div");
    footer.className = "card-footer";
    footer.append(createText("span", "badge", book.category_name));
    footer.append(createText("span", "meta", "查看书目 →"));
    article.append(footer);
    return article;
  };

  const setQueryString = () => {
    const params = new URLSearchParams();
    if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
    if (categorySelect.value) params.set("category", categorySelect.value);
    const query = params.toString();
    history.replaceState(null, "", query ? `?${query}` : location.pathname);
  };

  const start = async () => {
    try {
      const response = await fetch("catalog.json");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const books = await response.json();
      const params = new URLSearchParams(location.search);
      searchInput.value = params.get("q") || "";
      categorySelect.value = params.get("category") || "";

      const render = () => {
        const query = normalize(searchInput.value);
        const category = categorySelect.value;
        const filtered = books
          .filter((book) => !category || book.category === category)
          .filter((book) => {
            if (!query) return true;
            const haystack = normalize([
              book.clean_title,
              book.author,
              book.publisher,
              book.description,
              book.category_name,
              ...(book.tags || []),
            ].join(" "));
            return query.split(/\s+/).every((word) => haystack.includes(word));
          })
          .sort((a, b) => a.clean_title.localeCompare(b.clean_title, "zh-CN"));

        results.replaceChildren();
        summary.textContent = query || category
          ? `找到 ${filtered.length} 条符合条件的书目`
          : `当前共收录 ${filtered.length} 条书目`;

        if (!filtered.length) {
          const empty = createText("div", "empty-state", "没有找到匹配的书目，请尝试缩短关键词或更换分类。");
          results.append(empty);
        } else {
          filtered.forEach((book) => results.append(renderBook(book)));
        }
        setQueryString();
      };

      searchInput.addEventListener("input", render);
      categorySelect.addEventListener("change", render);
      render();
    } catch (error) {
      summary.textContent = "书目数据加载失败，请稍后重试。";
      results.replaceChildren(createText("div", "empty-state", "暂时无法读取 catalog.json。请确认网站通过 HTTP 服务运行。"));
      console.error(error);
    }
  };

  start();
})();
