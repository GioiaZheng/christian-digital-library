(() => {
  const endpoint = String(window.CDL_ACCESS_ENDPOINT || "").trim().replace(/\/+$/, "");
  const sections = Array.from(document.querySelectorAll("[data-book-opinions]"));

  if (!sections.length) return;

  function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function formatTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "刚刚";
    return new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function opinionUrl(bookId) {
    return `${endpoint}/book-opinions/${encodeURIComponent(bookId)}`;
  }

  function renderOpinions(list, opinions) {
    list.replaceChildren();

    if (!opinions.length) {
      list.append(createElement("p", "meta", "还没有看法，欢迎写第一条。"));
      return;
    }

    opinions
      .slice()
      .reverse()
      .forEach((opinion) => {
        const card = createElement("article", "book-opinion-card");
        const message = createElement("p", "", opinion.message || "");
        const meta = createElement(
          "small",
          "book-opinion-meta",
          `${opinion.name || "匿名读者"} · ${formatTime(opinion.created_at)}`,
        );
        card.append(message, meta);
        list.append(card);
      });
  }

  async function loadOpinions(section) {
    const bookId = section.dataset.bookId;
    const list = section.querySelector("[data-book-opinions-list]");
    const status = section.querySelector("[data-book-opinions-status]");
    if (!bookId || !list) return;

    if (!endpoint) {
      list.replaceChildren(createElement("p", "meta", "读者看法区正在接入中。"));
      return;
    }

    try {
      const response = await fetch(opinionUrl(bookId), {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("load failed");
      const data = await response.json();
      renderOpinions(list, Array.isArray(data.opinions) ? data.opinions : []);
      if (status) status.textContent = "";
    } catch (error) {
      list.replaceChildren(createElement("p", "meta", "读者看法暂时加载失败，可稍后再试。"));
    }
  }

  function attachForm(section) {
    const form = section.querySelector("[data-book-opinions-form]");
    const status = section.querySelector("[data-book-opinions-status]");
    const bookId = section.dataset.bookId;
    if (!form || !bookId) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const textarea = form.querySelector('textarea[name="message"]');
      const message = String(textarea?.value || "").trim();

      if (!message) {
        if (status) status.textContent = "请先写一点内容。";
        textarea?.focus();
        return;
      }

      if (!endpoint) {
        if (status) status.textContent = "读者看法区正在接入中。";
        return;
      }

      const submit = form.querySelector('button[type="submit"]');
      if (submit) submit.disabled = true;
      if (status) status.textContent = "正在发表……";

      try {
        const response = await fetch(opinionUrl(bookId), {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.message || "submit failed");

        if (textarea) textarea.value = "";
        if (status) status.textContent = "已发表。";
        await loadOpinions(section);
      } catch (error) {
        if (status) status.textContent = error.message || "发表失败，请稍后再试。";
      } finally {
        if (submit) submit.disabled = false;
      }
    });
  }

  sections.forEach((section) => {
    const refresh = section.querySelector("[data-book-opinions-refresh]");
    refresh?.addEventListener("click", () => loadOpinions(section));
    attachForm(section);
    loadOpinions(section);
  });
})();
