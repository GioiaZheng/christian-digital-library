(() => {
  const endpoint = String(window.CDL_UPLOAD_ENDPOINT || "").trim().replace(/\/+$/, "");
  const categoryNames = {
    "bible-study": "圣经研究",
    theology: "神学与教义",
    history: "教会历史",
    spirituality: "灵修与门徒训练",
    family: "婚姻家庭",
    society: "文化与社会",
    ministry: "事奉与宣教",
    biography: "传记与见证",
    reference: "工具书与参考",
    other: "其他",
  };

  let cachedOverrides = null;

  const cleanList = (value) => {
    const source = Array.isArray(value) ? value : String(value || "").split(/[、,，;；\n]+/);
    const seen = new Set();
    return source
      .map((item) => String(item || "").trim())
      .filter(Boolean)
      .filter((item) => {
        if (seen.has(item)) return false;
        seen.add(item);
        return true;
      });
  };

  const categoryLabel = (category) => categoryNames[category] || category || "其他";

  const normalizeOverride = (item) => {
    if (!item || !/^cdl-\d{6}$/.test(String(item.id || ""))) return null;
    const categories = cleanList(item.categories || item.category);
    const tags = cleanList(item.tags);
    const category = categories[0] || String(item.category || "").trim();
    return {
      ...item,
      id: String(item.id),
      clean_title: String(item.clean_title || "").trim(),
      author: String(item.author || "").trim(),
      publisher: String(item.publisher || "").trim(),
      year: String(item.year || "").trim(),
      category,
      categories,
      category_name: categoryLabel(category),
      tags,
      description: String(item.description || "").trim(),
      updated_at: String(item.updated_at || "").trim(),
    };
  };

  const loadOverrides = async () => {
    if (cachedOverrides) return cachedOverrides;
    if (!endpoint) {
      cachedOverrides = new Map();
      return cachedOverrides;
    }
    const response = await fetch(`${endpoint}/catalog-overrides`, { cache: "no-store" });
    if (!response.ok) throw new Error(`catalog-overrides HTTP ${response.status}`);
    const data = await response.json();
    cachedOverrides = new Map(
      (data.items || [])
        .map(normalizeOverride)
        .filter(Boolean)
        .map((item) => [item.id, item]),
    );
    return cachedOverrides;
  };

  const applyOverride = (book, override) => {
    if (!book || !override) return book;
    const next = { ...book };
    for (const key of ["clean_title", "author", "publisher", "year", "description", "updated_at"]) {
      if (override[key]) next[key] = override[key];
    }
    if (override.category) {
      next.category = override.category;
      next.category_name = override.category_name || categoryLabel(override.category);
    }
    if (override.categories?.length) next.categories = override.categories;
    if (override.tags?.length) next.tags = override.tags;
    return next;
  };

  const applyToBooks = async (books) => {
    const overrides = await loadOverrides().catch((error) => {
      console.warn("书目实时覆盖资料暂时无法读取。", error);
      return new Map();
    });
    return books.map((book) => applyOverride(book, overrides.get(book.id)));
  };

  const getBookOverride = async (bookId) => {
    const overrides = await loadOverrides().catch((error) => {
      console.warn("书目实时覆盖资料暂时无法读取。", error);
      return new Map();
    });
    return overrides.get(bookId) || null;
  };

  window.CDL_CATALOG_OVERRIDES = {
    applyToBooks,
    getBookOverride,
    categoryLabel,
  };
})();
