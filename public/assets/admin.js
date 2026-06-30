(() => {
  const endpoint = String(window.CDL_ADMIN_ENDPOINT || "").trim().replace(/\/+$/, "");
  const loginForm = document.querySelector("#admin-login-form");
  const loginStatus = document.querySelector("#admin-login-status");
  const panel = document.querySelector("#admin-panel");
  const refreshUploads = document.querySelector("#admin-refresh-uploads");
  const uploadList = document.querySelector("#admin-upload-list");
  const bookSearch = document.querySelector("#admin-book-search");
  const bookResults = document.querySelector("#admin-book-results");
  const bookForm = document.querySelector("#admin-book-form");
  const bookStatus = document.querySelector("#admin-book-status");

  if (!loginForm || !panel || !endpoint) return;

  let adminCode = "";
  let catalog = [];

  const setText = (target, value) => {
    if (target) target.textContent = value;
  };

  const adminUrl = (path) => `${endpoint}${path}`;

  const requestAdmin = async (path, options = {}) => {
    const headers = new Headers(options.headers || {});
    headers.set("X-CDL-Admin-Code", adminCode);
    if (options.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const response = await fetch(adminUrl(path), {
      ...options,
      headers,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || "请求失败。");
    }
    return data;
  };

  const createText = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  };

  const loadCatalog = async () => {
    if (catalog.length) return catalog;
    const response = await fetch("catalog.json");
    if (!response.ok) throw new Error("无法读取公开书目。");
    catalog = await response.json();
    return catalog;
  };

  const renderUploads = (items) => {
    uploadList.replaceChildren();
    if (!items.length) {
      uploadList.append(createText("div", "empty-state", "没有待审核上传。"));
      return;
    }

    for (const item of items) {
      const card = document.createElement("article");
      card.className = "admin-upload-card";
      const title = createText("h3", "", item.title || "未填书名");
      const meta = createText(
        "p",
        "meta",
        [item.author || "作者待核", item.filename || "未命名文件", item.status || "pending"].join(" · "),
      );
      const actions = document.createElement("div");
      actions.className = "admin-card-actions";

      const approve = document.createElement("button");
      approve.className = "button";
      approve.type = "button";
      approve.textContent = "通过";
      approve.addEventListener("click", async () => {
        approve.disabled = true;
        try {
          await requestAdmin(`/admin/uploads/${encodeURIComponent(item.id)}/approve`, { method: "POST" });
          await loadUploads();
        } catch (error) {
          setText(loginStatus, error.message || "审核失败。");
        } finally {
          approve.disabled = false;
        }
      });

      const reject = document.createElement("button");
      reject.className = "button secondary";
      reject.type = "button";
      reject.textContent = "拒绝";
      reject.addEventListener("click", async () => {
        reject.disabled = true;
        try {
          await requestAdmin(`/admin/uploads/${encodeURIComponent(item.id)}/reject`, { method: "POST" });
          await loadUploads();
        } catch (error) {
          setText(loginStatus, error.message || "审核失败。");
        } finally {
          reject.disabled = false;
        }
      });

      actions.append(approve, reject);
      card.append(title, meta, actions);
      uploadList.append(card);
    }
  };

  async function loadUploads() {
    setText(loginStatus, "正在读取待审核上传……");
    const data = await requestAdmin("/admin/uploads");
    renderUploads(data.items || []);
    setText(loginStatus, "已登录。");
  }

  const fillBookForm = (book) => {
    bookForm.hidden = false;
    bookForm.elements.namedItem("id").value = book.id || "";
    bookForm.elements.namedItem("clean_title").value = book.clean_title || "";
    bookForm.elements.namedItem("author").value = book.author || "";
    bookForm.elements.namedItem("publisher").value = book.publisher || "";
    bookForm.elements.namedItem("year").value = book.year || "";
    bookForm.elements.namedItem("category").value = book.category || "";
    bookForm.elements.namedItem("tags").value = Array.isArray(book.tags) ? book.tags.join("、") : "";
    bookForm.elements.namedItem("description").value = book.description || "";
    setText(bookStatus, `正在修改：${book.id}`);
    bookForm.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const renderBookResults = async () => {
    const value = String(bookSearch.value || "").trim().toLocaleLowerCase("zh-CN");
    bookResults.replaceChildren();
    if (!value) {
      bookResults.append(createText("div", "empty-state", "输入关键词后选择一本书。"));
      return;
    }
    const books = await loadCatalog();
    const matches = books
      .filter((book) =>
        [book.id, book.clean_title, book.author, book.category_name].join(" ").toLocaleLowerCase("zh-CN").includes(value),
      )
      .slice(0, 12);

    if (!matches.length) {
      bookResults.append(createText("div", "empty-state", "没有找到匹配书目。"));
      return;
    }

    for (const book of matches) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "admin-book-result";
      button.innerHTML = `<strong></strong><span></span>`;
      button.querySelector("strong").textContent = book.clean_title || book.id;
      button.querySelector("span").textContent = [book.id, book.author || "作者待核"].join(" · ");
      button.addEventListener("click", () => fillBookForm(book));
      bookResults.append(button);
    }
  };

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    adminCode = String(loginForm.elements.namedItem("admin_code")?.value || "").trim();
    if (!adminCode) {
      setText(loginStatus, "请输入管理员密码。");
      return;
    }
    try {
      await loadCatalog();
      await loadUploads();
      loginForm.hidden = true;
      panel.hidden = false;
    } catch (error) {
      adminCode = "";
      setText(loginStatus, error.message || "登录失败。");
    }
  });

  refreshUploads?.addEventListener("click", () => {
    loadUploads().catch((error) => setText(loginStatus, error.message || "刷新失败。"));
  });

  bookSearch?.addEventListener("input", () => {
    renderBookResults().catch((error) => setText(bookStatus, error.message || "搜索失败。"));
  });

  bookForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(bookForm).entries());
    const bookId = payload.id;
    delete payload.id;
    try {
      await requestAdmin(`/admin/books/${encodeURIComponent(bookId)}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setText(bookStatus, "已保存到后台。同步目录后会显示在公开网站。");
    } catch (error) {
      setText(bookStatus, error.message || "保存失败。");
    }
  });
})();
