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

  const start = async () => {
    const override = await window.CDL_CATALOG_OVERRIDES?.getBookOverride?.(bookId);
    if (!override) return;

    setText("[data-live-field='clean_title']", override.clean_title);
    setText("[data-live-field='author']", override.author || "作者信息待核实");
    setText("[data-live-field='description']", override.description || "暂无内容简介。");
    setMetadata("author", override.author || "待核实");
    setMetadata("publisher", override.publisher || "待核实");
    setMetadata("year", override.year || "待核实");
    setMetadata("category", override.category_name || override.category);
    renderTags(override.tags);

    if (override.clean_title) {
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
