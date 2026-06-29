(() => {
  const input = document.querySelector("#category-search-input");
  const results = document.querySelector("#category-results");
  const summary = document.querySelector("#category-result-summary");
  const emptyState = document.querySelector("#category-empty-state");

  if (!input || !results || !summary || !emptyState) return;

  const cards = Array.from(results.querySelectorAll(".card"));
  const total = Number(results.dataset.categoryTotal || cards.length);
  const normalize = (value) => String(value || "").trim().toLocaleLowerCase("zh-CN");

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

  const params = new URLSearchParams(location.search);
  input.value = params.get("q") || "";
  input.addEventListener("input", render);
  if (!cards.length) {
    input.disabled = true;
    emptyState.hidden = true;
    return;
  }
  render();
})();
