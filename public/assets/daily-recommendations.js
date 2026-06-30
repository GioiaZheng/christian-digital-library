(() => {
  const container = document.querySelector("#daily-recommendations");
  if (!container) return;

  const todayKey = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const hashSeed = (value) => {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  };

  const randomFromSeed = (seed) => {
    let state = seed || 1;
    return () => {
      state = Math.imul(1664525, state) + 1013904223;
      return (state >>> 0) / 4294967296;
    };
  };

  const createText = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  };

  const goodRecommendation = (book) => {
    const title = String(book.clean_title || "").trim();
    if (!title || /^[0-9A-Za-z]{3,}/.test(title)) return false;
    if (/待核|未整理|无标题/.test(title)) return false;
    return true;
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

    article.append(createText("p", "meta", book.author || "作者待核"));
    const footer = document.createElement("div");
    footer.className = "card-footer";
    footer.append(createText("span", "badge", book.category_name || "馆藏"));
    footer.append(createText("span", "meta", "查看书目 →"));
    article.append(footer);
    return article;
  };

  const pickDailyBooks = (books) => {
    const candidates = books.filter(goodRecommendation);
    const random = randomFromSeed(hashSeed(todayKey()));
    const pool = [...candidates];
    const picked = [];
    while (pool.length && picked.length < 5) {
      const index = Math.floor(random() * pool.length);
      picked.push(pool.splice(index, 1)[0]);
    }
    return picked;
  };

  const start = async () => {
    try {
      const response = await fetch("catalog.json");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const books = await response.json();
      const picked = pickDailyBooks(books);
      container.replaceChildren();
      if (!picked.length) {
        container.append(createText("div", "empty-state", "今日推荐正在整理中。"));
        return;
      }
      picked.forEach((book) => container.append(renderBook(book)));
    } catch (error) {
      container.replaceChildren(createText("div", "empty-state", "今日推荐暂时无法加载。"));
      console.error(error);
    }
  };

  start();
})();
