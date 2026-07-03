(() => {
  const marker = document.querySelector("[data-book-detail-id]");
  if (!marker) return;

  const bookId = marker.dataset.bookDetailId;
  const setText = (selector, value) => {
    const element = document.querySelector(selector);
    if (element && value) element.textContent = value;
  };

  const setMetadata = (name, value) => {
    const element = document.querySelector(`[data-live-metadata="${CSS.escape(name)}"]`);
    if (element && value) element.textContent = value;
  };

  const renderTags = (tags) => {
    const container = document.querySelector("[data-live-tags]");
    if (!container || !Array.isArray(tags) || !tags.length) return;
    container.replaceChildren();
    for (const tag of tags) {
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
    for (const item of items.filter(Boolean)) {
      const li = document.createElement("li");
      li.textContent = item;
      container.append(li);
    }
    const empty = document.querySelector("[data-live-toc-empty]");
    if (empty) empty.hidden = container.children.length > 0;
  };

  const start = async () => {
    const override = await window.CDL_CATALOG_OVERRIDES?.getBookOverride?.(bookId);
    const originalAuthor = String(marker.dataset.bookAuthor || "").trim();
    const authorName = override?.author || originalAuthor;
    const sharedAuthorBio = await window.CDL_CATALOG_OVERRIDES?.getAuthorBio?.(authorName);
    if (!override && !sharedAuthorBio) return;

    setText("[data-live-field='clean_title']", override?.clean_title);
    setText("[data-live-field='author']", override?.author || (override ? "作者信息整理中" : ""));
    setText("[data-live-field='description']", override?.description || (override ? "简介待补充。" : ""));
    setText("[data-live-field='author_bio']", override?.author_bio || sharedAuthorBio || (override ? "作者介绍待补充。" : ""));
    setMetadata("author", override?.author || (override ? "作者信息整理中" : ""));
    setMetadata("translator", override?.translator || (override ? "译者信息整理中" : ""));
    setMetadata("publisher", override?.publisher || (override ? "出版信息整理中" : ""));
    setMetadata("year", override?.year || (override ? "出版信息整理中" : ""));
    setMetadata("category", override?.category_name || override?.category);
    renderTags(override?.tags);
    renderToc(override?.table_of_contents);

    if (override?.clean_title) {
      document.title = `${override.clean_title}｜基督教数字图书馆`;
      document.querySelectorAll("[data-live-title-attr]").forEach((element) => {
        if (element instanceof HTMLImageElement) {
          element.alt = element.alt.replace(/^.*?(?= 第|\s*封面|$)/, override.clean_title);
        } else {
          element.dataset.mediaCaption = element.dataset.mediaCaption?.replace(/^.*?(?= ·|$)/, override.clean_title) || "";
        }
      });
    }
  };

  start().catch((error) => console.warn("书目实时资料暂时无法读取。", error));
})();
