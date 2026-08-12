(() => {
  const marker = document.querySelector("[data-book-detail-id]");
  if (!marker) return;

  const bookId = marker.dataset.bookDetailId;
  const isCorruptText = (value) => /\?{2,}/.test(String(value || "")) || /�{2,}/.test(String(value || ""));
  const cleanValue = (value) => {
    const text = String(value || "").trim();
    return isCorruptText(text) ? "" : text;
  };

  const normalizeComparableText = (value) =>
    String(value || "")
      .replace(/[()\[\]（）【】《》〈〉:：·.\s_-]+/g, "")
      .trim();

  const isSuspiciousShortOverride = (currentValue, overrideValue) => {
    const current = normalizeComparableText(currentValue);
    const override = normalizeComparableText(overrideValue);
    if (!current || !override) return false;
    return current.length >= override.length + 4 && current.includes(override);
  };
  const cleanListValue = (value) => {
    const list = Array.isArray(value) ? value : String(value || "").split(/[;；、,，]/);
    return list.map(cleanValue).filter(Boolean).join("、");
  };

  const setText = (selector, value) => {
    const element = document.querySelector(selector);
    const text = cleanValue(value);
    if (element && text) element.textContent = text;
  };

  const setMetadata = (name, value) => {
    const text = cleanValue(value);
    if (!text) return;
    document.querySelectorAll("[data-live-metadata]").forEach((element) => {
      if (element.dataset.liveMetadata === name) element.textContent = text;
    });
  };

  const renderTags = (tags) => {
    const container = document.querySelector("[data-live-tags]");
    if (!container || !Array.isArray(tags) || !tags.length) return;
    container.replaceChildren();
    for (const rawTag of tags) {
      const tag = cleanValue(rawTag);
      if (!tag) continue;
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = tag;
      container.append(span);
    }
  };

  const renderToc = (items) => {
    const container = document.querySelector("[data-live-toc]");
    if (!container || !Array.isArray(items)) return;
    container.replaceChildren();
    for (const rawItem of items) {
      const item = cleanValue(rawItem);
      if (!item) continue;
      const li = document.createElement("li");
      li.textContent = item;
      container.append(li);
    }
    const empty = document.querySelector("[data-live-toc-empty]");
    if (empty) empty.hidden = container.children.length > 0;
  };

  const applyOverride = (override) => {
    if (!override) return;
    const author = cleanListValue(override?.authors || override?.author);
    const translator = cleanListValue(override?.translators || override?.translator);

    const originalTitle = String(marker.dataset.bookTitle || "").trim();
    const titleOverride = isSuspiciousShortOverride(originalTitle, override?.clean_title) ? "" : override?.clean_title;
    setText("[data-live-field='clean_title']", titleOverride);
    setText("[data-live-field='author']", author);
    setText("[data-live-field='description']", override?.description || "");
    setText("[data-live-field='author_bio']", override?.author_bio || "");
    setMetadata("author", author);
    setMetadata("translator", translator);
    setMetadata("publisher", override?.publisher || "");
    setMetadata("year", override?.year || "");
    setMetadata("category", override?.category_name || override?.category);
    renderTags(override?.tags);
    renderToc(override?.table_of_contents);

    const cleanTitle = cleanValue(titleOverride);
    if (cleanTitle) {
      document.title = `${cleanTitle}｜基督教数字图书馆`;
      document.querySelectorAll("[data-live-title-attr]").forEach((element) => {
        if (element instanceof HTMLImageElement) {
          element.alt = element.alt.replace(/^.*?(?= 第|\s*封面|$)/, cleanTitle);
        } else {
          element.dataset.mediaCaption = element.dataset.mediaCaption?.replace(/^.*?(?= ·|$)/, cleanTitle) || "";
        }
      });
    }
  };

  const start = async () => {
    const override =
      (await window.CDL_CATALOG_OVERRIDES?.getFreshBookOverride?.(bookId)) ||
      (await window.CDL_CATALOG_OVERRIDES?.getBookOverride?.(bookId));
    applyOverride(override);

    const originalAuthor = String(marker.dataset.bookAuthor || "").trim();
    const authorName = cleanListValue(override?.authors || override?.author) || originalAuthor;
    if (override?.author_bio) return;

    const sharedAuthorBio = await window.CDL_CATALOG_OVERRIDES?.getAuthorBio?.(authorName);
    setText("[data-live-field='author_bio']", sharedAuthorBio || "");
  };

  start().catch((error) => console.warn("书目实时资料暂时无法读取。", error));
})();
