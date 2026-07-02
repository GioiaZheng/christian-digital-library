(() => {
  const input = document.querySelector("#category-search-input");
  const results = document.querySelector("#category-results");
  const summary = document.querySelector("#category-result-summary");
  const emptyState = document.querySelector("#category-empty-state");

  if (!input || !results || !summary || !emptyState) return;

  const pageCategory = String(results.dataset.categoryId || "").trim();
  const normalize = (value) => String(value || "").trim().toLocaleLowerCase("zh-CN");
  let categoryBooks = [];

  const createText = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  };

  const appendAuthorByline = (container, book) => {
    const meta = document.createElement("p");
    meta.className = "meta";
    if (book.author && book.author_url) {
      const link = document.createElement("a");
      link.className = "author-link";
      link.href = `../${book.author_url}`;
      link.textContent = book.author;
      meta.append(link);
    } else {
      meta.append(document.createTextNode(book.author || "作者信息整理中"));
    }
    for (const part of [book.translator ? `译者：${book.translator}` : "", book.year].filter(Boolean)) {
      meta.append(document.createTextNode(` · ${part}`));
    }
    container.append(meta);
  };

  const bookInCategory = (book) => {
    const categories = Array.isArray(book.categories) && book.categories.length ? book.categories : [book.category];
    return categories.map(String).includes(pageCategory);
  };

  const renderBook = (book) => {
    const article = document.createElement("article");
    article.className = "card";
    article.dataset.catalogBookId = book.id;
    article.dataset.filterText = [
      book.clean_title,
      book.author,
      book.translator,
      book.publisher,
      book.description,
      book.category_name,
      ...(book.category_names || []),
      ...(book.tags || []),
    ]
      .filter(Boolean)
      .join(" ");

    const title = document.createElement("h3");
    const link = document.createElement("a");
    link.href = `../${book.detail_url || `books/${book.id}.html`}`;
    link.textContent = book.clean_title || book.id;
    title.append(link);
    article.append(title);

    appendAuthorByline(article, book);
    if (book.description) {
      article.append(createText("p", "description", book.description));
    }
    const footer = document.createElement("div");
    footer.className = "card-footer";
    footer.append(createText("span", "badge", book.category_name || "其他"));
    footer.append(createText("span", "meta", "查看书目 →"));
    article.append(footer);
    return article;
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
    const matched = categoryBooks.filter((book) => {
      if (!words.length) return true;
      const haystack = normalize([
        book.clean_title,
        book.author,
        book.translator,
        book.publisher,
        book.description,
        book.category_name,
        ...(book.category_names || []),
        ...(book.tags || []),
      ].join(" "));
      return words.every((word) => haystack.includes(word));
    });

    results.replaceChildren();
    matched.forEach((book) => results.append(renderBook(book)));

    if (words.length) {
      summary.textContent = `共 ${categoryBooks.length} 条书目，筛选出 ${matched.length} 条`;
    } else {
      summary.textContent = `共 ${categoryBooks.length} 条书目`;
    }
    emptyState.hidden = matched.length !== 0;
    setQueryString();
  };

  const fallbackToStaticCards = () => {
    const cards = Array.from(results.querySelectorAll(".card"));
    categoryBooks = cards.map((card) => ({
      id: card.dataset.catalogBookId || "",
      clean_title: card.querySelector("[data-card-title]")?.textContent || card.querySelector("h3")?.textContent || "",
      author: card.querySelector("[data-card-byline]")?.textContent || "",
      translator: "",
      category_name: card.querySelector("[data-card-category]")?.textContent || "",
      description: card.querySelector("[data-card-description]")?.textContent || "",
      detail_url: card.querySelector("a")?.getAttribute("href")?.replace(/^\.\.\//, "") || "",
    }));
    render();
  };

  const start = async () => {
    const params = new URLSearchParams(location.search);
    input.value = params.get("q") || "";
    input.addEventListener("input", render);

    try {
      const response = await fetch("../catalog.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const catalog = await response.json();
      const books = window.CDL_CATALOG_OVERRIDES?.applyToBooks
        ? await window.CDL_CATALOG_OVERRIDES.applyToBooks(catalog)
        : catalog;
      categoryBooks = books.filter(bookInCategory);
      results.dataset.categoryTotal = String(categoryBooks.length);
      render();
    } catch (error) {
      console.warn("分类页实时书目资料暂时无法读取，使用静态内容。", error);
      fallbackToStaticCards();
    }
  };

  start();
})();
