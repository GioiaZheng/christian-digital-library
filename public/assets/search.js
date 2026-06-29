(() => {
  const searchInput = document.querySelector("#search-input");
  const categorySelect = document.querySelector("#category-filter");
  const results = document.querySelector("#search-results");
  const summary = document.querySelector("#result-summary");
  const loadMore = document.querySelector("#load-more");

  if (!searchInput || !categorySelect || !results || !summary || !loadMore) return;

  const pageSize = 48;
  let visibleCount = pageSize;

  const normalize = (value) => String(value || "").trim().toLocaleLowerCase("zh-CN");
  const sortTitle = (value) =>
    String(value || "")
      .trim()
      .replace(/^\d{7,}[：:\s]+/, "")
      .replace(/^(?:\d{1,4}[\s、.．：:\-]+)+/, "")
      .replace(/^\d{1,3}(?=[\u3400-\u9fff])/, "");

  const compareBooks = (a, b) => {
    const aTitle = String(a.clean_title || "").trim();
    const bTitle = String(b.clean_title || "").trim();
    const aNoisy = /^[0-9A-Za-z]/.test(aTitle) ? 1 : 0;
    const bNoisy = /^[0-9A-Za-z]/.test(bTitle) ? 1 : 0;
    if (aNoisy !== bNoisy) return aNoisy - bNoisy;
    return (sortTitle(aTitle) || aTitle).localeCompare(sortTitle(bTitle) || bTitle, "zh-CN");
  };

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
    if (book.description) {
      article.append(createText("p", "description", book.description));
    }

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

      const render = (resetVisible = false) => {
        if (resetVisible) visibleCount = pageSize;
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
          .sort(compareBooks);

        const visibleBooks = filtered.slice(0, visibleCount);
        results.replaceChildren();
        summary.textContent = `找到 ${filtered.length} 条书目，当前显示 ${visibleBooks.length} 条`;

        if (!filtered.length) {
          const empty = createText("div", "empty-state", "没有找到匹配的书目，请尝试缩短关键词或更换分类。");
          results.append(empty);
        } else {
          visibleBooks.forEach((book) => results.append(renderBook(book)));
        }
        loadMore.hidden = visibleBooks.length >= filtered.length;
        setQueryString();
      };

      searchInput.addEventListener("input", () => render(true));
      categorySelect.addEventListener("change", () => render(true));
      loadMore.addEventListener("click", () => {
        visibleCount += pageSize;
        render();
      });
      render();
    } catch (error) {
      summary.textContent = "书目数据加载失败，请稍后重试。";
      results.replaceChildren(createText("div", "empty-state", "暂时无法读取 catalog.json。请确认网站通过 HTTP 服务运行。"));
      console.error(error);
    }
  };

  start();
})();
