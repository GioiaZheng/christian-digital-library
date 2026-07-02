(() => {
  const searchInput = document.querySelector("#search-input");
  const categorySelect = document.querySelector("#category-filter");
  const results = document.querySelector("#search-results");
  const summary = document.querySelector("#result-summary");
  const sentinel = document.querySelector("#catalog-scroll-sentinel");
  const alphabetIndex = document.querySelector("#alphabet-index");

  if (!searchInput || !categorySelect || !results || !summary || !sentinel) return;

  const pageSize = 48;
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
  const chineseInitialLetters = "ABCDEFGHJKLMNOPQRSTWXYZ".split("");
  const chineseBoundaries = "阿八嚓咑妸发旮哈讥咔垃妈拏噢妑七呥仨他哇夕丫帀".split("");
  const pinyinCollator = new Intl.Collator("zh-CN-u-co-pinyin");

  let visibleCount = pageSize;
  let allBooks = [];
  let filteredBooks = [];
  let isRendering = false;

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

  const initialOfTitle = (value) => {
    const title = sortTitle(value);
    const match = title.match(/[A-Za-z\u3400-\u9fff]/);
    const char = match?.[0] || "";
    if (!char) return "#";
    if (/^[A-Za-z]$/.test(char)) return char.toUpperCase();
    let index = -1;
    for (let i = 0; i < chineseBoundaries.length; i += 1) {
      if (pinyinCollator.compare(char, chineseBoundaries[i]) >= 0) {
        index = i;
      } else {
        break;
      }
    }
    return index >= 0 ? chineseInitialLetters[index] : "#";
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
    article.dataset.catalogBookId = book.id;
    article.dataset.catalogInitial = initialOfTitle(book.clean_title);

    const title = document.createElement("h3");
    const link = document.createElement("a");
    link.href = book.detail_url;
    link.textContent = book.clean_title;
    title.append(link);
    article.append(title);

    const bylineParts = [
      book.author || "作者待核",
      book.translator ? `译者：${book.translator}` : "",
      book.year,
    ].filter(Boolean);
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

  const renderAlphabet = () => {
    if (!alphabetIndex) return;
    const present = new Set(filteredBooks.map((book) => initialOfTitle(book.clean_title)));
    alphabetIndex.replaceChildren();
    for (const letter of letters) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = letter;
      button.disabled = !present.has(letter);
      button.addEventListener("click", () => {
        const firstIndex = filteredBooks.findIndex((book) => initialOfTitle(book.clean_title) === letter);
        if (firstIndex < 0) return;
        visibleCount = Math.max(visibleCount, firstIndex + 1);
        render(false, { scrollToBookId: filteredBooks[firstIndex].id });
      });
      alphabetIndex.append(button);
    }
  };

  const filterBooks = () => {
    const query = normalize(searchInput.value);
    const category = categorySelect.value;
    return allBooks
      .filter((book) => {
        if (!category) return true;
        const categories = Array.isArray(book.categories) && book.categories.length ? book.categories : [book.category];
        return categories.map(String).includes(category);
      })
      .filter((book) => {
        if (!query) return true;
        const haystack = normalize([
          book.clean_title,
          book.author,
          book.translator,
          book.publisher,
          book.description,
          book.category_name,
          ...(book.tags || []),
        ].join(" "));
        return query.split(/\s+/).every((word) => haystack.includes(word));
      })
      .sort(compareBooks);
  };

  const render = (resetVisible = false, options = {}) => {
    if (isRendering) return;
    isRendering = true;
    if (resetVisible) visibleCount = pageSize;

    filteredBooks = filterBooks();
    const visibleBooks = filteredBooks.slice(0, visibleCount);
    results.replaceChildren();
    summary.textContent = `找到 ${filteredBooks.length} 条书目，当前显示 ${visibleBooks.length} 条`;

    if (!filteredBooks.length) {
      results.append(createText("div", "empty-state", "没有找到匹配的书目，请尝试缩短关键词或更换分类。"));
    } else {
      visibleBooks.forEach((book) => results.append(renderBook(book)));
    }

    sentinel.hidden = visibleBooks.length >= filteredBooks.length;
    sentinel.textContent = sentinel.hidden ? "" : "继续向下滑动加载更多";
    renderAlphabet();
    setQueryString();

    if (options.scrollToBookId) {
      const target = results.querySelector(`[data-catalog-book-id="${CSS.escape(options.scrollToBookId)}"]`);
      target?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    isRendering = false;
  };

  const loadNextPage = () => {
    if (visibleCount >= filteredBooks.length) return;
    visibleCount += pageSize;
    render();
  };

  const start = async () => {
    try {
      const response = await fetch("catalog.json");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const books = await response.json();
      allBooks = window.CDL_CATALOG_OVERRIDES?.applyToBooks
        ? await window.CDL_CATALOG_OVERRIDES.applyToBooks(books)
        : books;
      const params = new URLSearchParams(location.search);
      searchInput.value = params.get("q") || "";
      categorySelect.value = params.get("category") || "";

      searchInput.addEventListener("input", () => render(true));
      categorySelect.addEventListener("change", () => render(true));

      if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(
          (entries) => {
            if (entries.some((entry) => entry.isIntersecting)) loadNextPage();
          },
          { rootMargin: "420px 0px" },
        );
        observer.observe(sentinel);
      } else {
        window.addEventListener(
          "scroll",
          () => {
            if (sentinel.hidden) return;
            const rect = sentinel.getBoundingClientRect();
            if (rect.top < window.innerHeight + 320) loadNextPage();
          },
          { passive: true },
        );
      }

      render();
    } catch (error) {
      summary.textContent = "书目数据加载失败，请稍后重试。";
      results.replaceChildren(createText("div", "empty-state", "暂时无法读取 catalog.json。请确认网站通过 HTTP 服务运行。"));
      console.error(error);
    }
  };

  start();
})();
