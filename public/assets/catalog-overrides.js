(() => {
  const endpoint = String(window.CDL_UPLOAD_ENDPOINT || "").trim().replace(/\/+$/, "");
  const categoryNames = {
    "bible-study": "圣经研究",
    theology: "神学与教义",
    "church-history": "教会历史",
    "spiritual-life": "灵修与门徒训练",
    pastoral: "讲道与牧养",
    missions: "宣教与福音",
    "family-ministry": "婚姻家庭",
    "culture-society": "文化与社会",
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
  const categoryLabels = (categories) => cleanList(categories).map(categoryLabel);

  const normalizeOverride = (item) => {
    if (!item || !/^cdl-\d{6}$/.test(String(item.id || ""))) return null;
    const categories = cleanList(item.categories || item.category);
    const tags = cleanList(item.tags);
    const category = categories[0] || String(item.category || "").trim();
    const names = categoryLabels(categories.length ? categories : [category]);
    return {
      ...item,
      id: String(item.id),
      clean_title: String(item.clean_title || "").trim(),
      author: String(item.author || "").trim(),
      author_bio: String(item.author_bio || "").trim(),
      translator: String(item.translator || "").trim(),
      publisher: String(item.publisher || "").trim(),
      year: String(item.year || "").trim(),
      category,
      categories,
      category_name: names[0] || categoryLabel(category),
      category_names: names,
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
    for (const key of ["clean_title", "author", "author_bio", "translator", "publisher", "year", "description", "updated_at"]) {
      if (override[key]) next[key] = override[key];
    }
    if (override.category) {
      next.category = override.category;
      next.category_name = override.category_name || categoryLabel(override.category);
    }
    if (override.categories?.length) next.categories = override.categories;
    if (override.category_names?.length) next.category_names = override.category_names;
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
