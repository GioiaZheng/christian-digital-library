(() => {
  const endpoint = String(window.CDL_ADMIN_ENDPOINT || "").trim().replace(/\/+$/, "");
  const loginForm = document.querySelector("#admin-login-form");
  const loginStatus = document.querySelector("#admin-login-status");
  const panel = document.querySelector("#admin-panel");
  const refreshUploads = document.querySelector("#admin-refresh-uploads");
  const uploadList = document.querySelector("#admin-upload-list");
  const addBookForm = document.querySelector("#admin-add-book-form");
  const addBookStatus = document.querySelector("#admin-add-status");
  const bookSearch = document.querySelector("#admin-book-search");
  const bookResults = document.querySelector("#admin-book-results");
  const bookForm = document.querySelector("#admin-book-form");
  const bookStatus = document.querySelector("#admin-book-status");
  const readingSummary = document.querySelector("#admin-reading-summary");
  const readingList = document.querySelector("#admin-reading-list");
  const categoryList = document.querySelector("#admin-book-category-list");
  const newCategoryInput = document.querySelector("#admin-new-category");
  const addCategoryButton = document.querySelector("#admin-add-category");

  if (!loginForm || !panel || !endpoint) return;

  let adminCode = "";
  let catalog = [];
  let categories = [];
  let readingStatuses = new Map();
  const readingStatusOptions = [
    { value: "want_to_read", label: "想读" },
    { value: "finished", label: "读完" },
  ];
  const allowedAdminExtensions = new Set(["pdf", "epub", "mobi"]);

  const setText = (target, value) => {
    if (target) target.textContent = value;
  };

  const setStatusWithPublicLink = (target, message, bookId) => {
    if (!target) return;
    target.replaceChildren();
    target.append(document.createTextNode(message));
    if (!bookId) return;
    target.append(document.createTextNode(" "));
    const link = document.createElement("a");
    link.href = `books/${encodeURIComponent(bookId)}.html`;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "查看公开页面 →";
    target.append(link);
  };

  const adminUrl = (path) => `${endpoint}${path}`;

  const requestAdmin = async (path, options = {}) => {
    const headers = new Headers(options.headers || {});
    headers.set("X-CDL-Admin-Code", adminCode);
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
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

  const splitList = (value) => {
    const seen = new Set();
    return String(value || "")
      .split(/[、,，;；\n]+/)
      .map((item) => item.trim())
      .filter(Boolean)
      .filter((item) => {
        if (seen.has(item)) return false;
        seen.add(item);
        return true;
      });
  };

  const normalizeCategoryKey = (value) => String(value || "").trim().toLocaleLowerCase("zh-CN");

  const categoryLabel = (categoryValue) => {
    const value = String(categoryValue || "").trim();
    const matched = categories.find((category) => category.id === value || category.name === value);
    return matched?.name || value || "其他";
  };

  const normalizeCategories = (values) => {
    const source = Array.isArray(values) ? values : splitList(values);
    const seen = new Set();
    const result = [];
    for (const raw of source) {
      const value = String(raw || "").trim();
      if (!value) continue;
      const matched = categories.find((category) => category.id === value || category.name === value);
      const normalized = matched?.id || value;
      const key = normalizeCategoryKey(matched?.name || normalized);
      if (seen.has(key)) continue;
      seen.add(key);
      result.push(normalized);
    }
    return result;
  };

  const ensureCategoryOption = (value) => {
    const name = String(value || "").trim();
    if (!name) return null;
    const matched = categories.find(
      (category) => category.id === name || normalizeCategoryKey(category.name) === normalizeCategoryKey(name),
    );
    if (matched) return matched;
    const custom = { id: name, name, description: "" };
    categories.push(custom);
    renderCategoryCheckboxes();
    return custom;
  };

  const selectedCategories = () => {
    if (!categoryList) return [];
    return Array.from(categoryList.querySelectorAll("input[type='checkbox']:checked")).map((input) => input.value);
  };

  const setSelectedCategories = (values) => {
    const normalized = normalizeCategories(values);
    for (const value of normalized) ensureCategoryOption(value);
    const selected = new Set(normalized);
    categoryList?.querySelectorAll("input[type='checkbox']").forEach((input) => {
      input.checked = selected.has(input.value);
    });
  };

  function renderCategoryCheckboxes() {
    if (!categoryList) return;
    const selected = new Set(selectedCategories());
    categoryList.replaceChildren();
    categories.forEach((category) => {
      const label = document.createElement("label");
      label.className = "checkbox-option";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "categories";
      input.value = category.id;
      input.checked = selected.has(category.id);
      const span = document.createElement("span");
      span.textContent = category.name;
      label.append(input, span);
      categoryList.append(label);
    });
  }

  const extensionOf = (filename) => {
    const match = /\.([A-Za-z0-9]+)$/.exec(String(filename || ""));
    return match ? match[1].toLowerCase() : "";
  };

  const validateAdminBookFile = (formData) => {
    const file = formData.get("file");
    if (!(file instanceof File) || !file.name) {
      return "请选择整理后的书籍文件。";
    }
    if (!allowedAdminExtensions.has(extensionOf(file.name))) {
      return "请上传 PDF、EPUB 或 MOBI 文件，不要上传 ZIP。";
    }
    const maxBytes = Number(addBookForm?.dataset.maxBytes || 104857600);
    if (Number.isFinite(maxBytes) && maxBytes > 0 && file.size > maxBytes) {
      const maxMb = Math.floor(maxBytes / 1024 / 1024);
      return `文件太大，单个文件最大 ${maxMb} MB。`;
    }
    return "";
  };

  const loadCatalog = async () => {
    if (catalog.length) return catalog;
    const response = await fetch("catalog.json");
    if (!response.ok) throw new Error("无法读取公开书目。");
    catalog = await response.json();
    return catalog;
  };

  const loadCategories = async () => {
    if (categories.length) return categories;
    const response = await fetch("categories.json");
    if (!response.ok) throw new Error("无法读取分类列表。");
    categories = await response.json();
    renderCategoryCheckboxes();
    return categories;
  };

  const statusLabel = (status) => {
    const option = readingStatusOptions.find((item) => item.value === status);
    return option ? option.label : "";
  };

  const loadReadingStatuses = async () => {
    const data = await requestAdmin("/admin/reading-status");
    readingStatuses = new Map((data.items || []).map((item) => [item.id, item]));
    renderReadingList();
  };

  const findCatalogBook = (bookId) => catalog.find((book) => book.id === bookId);

  const renderReadingList = () => {
    if (!readingList) return;
    readingList.replaceChildren();
    const items = Array.from(readingStatuses.values());
    const wantCount = items.filter((item) => item.status === "want_to_read").length;
    const finishedCount = items.filter((item) => item.status === "finished").length;
    setText(readingSummary, `想读 ${wantCount} 本，读完 ${finishedCount} 本。`);

    if (!items.length) {
      readingList.append(createText("div", "empty-state", "还没有标记书籍。可以在下面搜索书目后标记。"));
      return;
    }

    for (const item of items.slice(0, 18)) {
      const book = findCatalogBook(item.id) || { id: item.id, clean_title: item.id, author: "" };
      const card = document.createElement("article");
      card.className = "admin-reading-card";
      const title = document.createElement("a");
      title.href = book.detail_url || `books/${item.id}.html`;
      title.target = "_blank";
      title.rel = "noreferrer";
      title.textContent = book.clean_title || item.id;
      const meta = createText("p", "meta", [book.author || "作者信息整理中", item.label || statusLabel(item.status)].join(" · "));
      const actions = createReadingActions(book);
      card.append(title, meta, actions);
      readingList.append(card);
    }
  };

  const saveReadingStatus = async (book, status) => {
    const bookId = book.id;
    const data = await requestAdmin(`/admin/books/${encodeURIComponent(bookId)}/reading-status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    if (data.item?.status && data.item.status !== "none") {
      readingStatuses.set(bookId, data.item);
      setText(bookStatus, `已标记《${book.clean_title || bookId}》为${data.item.label}。`);
    } else {
      readingStatuses.delete(bookId);
      setText(bookStatus, `已取消《${book.clean_title || bookId}》的阅读标记。`);
    }
    renderReadingList();
    await renderBookResults();
  };

  function createReadingActions(book) {
    const actions = document.createElement("div");
    actions.className = "admin-reading-actions";
    const current = readingStatuses.get(book.id)?.status || "";

    for (const option of readingStatusOptions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `button secondary compact${current === option.value ? " is-active" : ""}`;
      button.textContent = option.label;
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await saveReadingStatus(book, option.value);
        } catch (error) {
          setText(bookStatus, error.message || "标记失败。");
        } finally {
          button.disabled = false;
        }
      });
      actions.append(button);
    }

    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "button ghost compact";
    clear.textContent = "取消";
    clear.disabled = !current;
    clear.addEventListener("click", async () => {
      clear.disabled = true;
      try {
        await saveReadingStatus(book, "none");
      } catch (error) {
        setText(bookStatus, error.message || "取消失败。");
      } finally {
        clear.disabled = false;
      }
    });
    actions.append(clear);
    return actions;
  }

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
        [item.author || "作者信息整理中", item.filename || "未命名文件", item.status || "pending"].join(" · "),
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
    bookForm.elements.namedItem("author_bio").value = book.author_bio || "";
    bookForm.elements.namedItem("translator").value = book.translator || "";
    bookForm.elements.namedItem("publisher").value = book.publisher || "";
    bookForm.elements.namedItem("year").value = book.year || "";
    setSelectedCategories(
      Array.isArray(book.categories) && book.categories.length ? book.categories : [book.category || book.category_name],
    );
    bookForm.elements.namedItem("tags").value = Array.isArray(book.tags) ? book.tags.join("、") : String(book.tags || "");
    bookForm.elements.namedItem("description").value = book.description || "";
    setText(bookStatus, `正在修改：${book.id}`);
    bookForm.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const applySavedBook = (bookId, override) => {
    const index = catalog.findIndex((book) => book.id === bookId);
    if (index < 0 || !override) return;
    const current = catalog[index];
    const category = override.category || current.category;
    const categories = normalizeCategories(override.categories || category);
    catalog[index] = {
      ...current,
      ...override,
      category: categories[0] || category,
      categories,
      category_name: categoryLabel(categories[0] || category),
      detail_url: current.detail_url,
    };
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
        [book.id, book.clean_title, book.author, book.translator, book.category_name]
          .join(" ")
          .toLocaleLowerCase("zh-CN")
          .includes(value),
      )
      .slice(0, 12);

    if (!matches.length) {
      bookResults.append(createText("div", "empty-state", "没有找到匹配书目。"));
      return;
    }

    for (const book of matches) {
      const card = document.createElement("article");
      card.className = "admin-book-result";

      const button = document.createElement("button");
      button.type = "button";
      button.className = "admin-book-result-main";
      button.innerHTML = `<strong></strong><span></span>`;
      button.querySelector("strong").textContent = book.clean_title || book.id;
      const status = readingStatuses.get(book.id);
      button.querySelector("span").textContent = [
        book.id,
        book.author || "作者信息整理中",
        book.translator ? `译者：${book.translator}` : "",
        status?.label ? `已标记：${status.label}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
      button.addEventListener("click", () => fillBookForm(book));

      card.append(button, createReadingActions(book));
      bookResults.append(card);
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
      await loadCategories();
      await loadCatalog();
      await loadReadingStatuses();
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

  addBookForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(addBookForm);
    const validationMessage = validateAdminBookFile(formData);
    if (validationMessage) {
      setText(addBookStatus, validationMessage);
      return;
    }

    const submit = addBookForm.querySelector('button[type="submit"]');
    if (submit) submit.disabled = true;
    setText(addBookStatus, "正在添加到后台，请不要关闭页面。");

    try {
      const data = await requestAdmin("/admin/books", {
        method: "POST",
        body: formData,
      });
      addBookForm.reset();
      setText(addBookStatus, `已添加《${data.item?.title || "新书"}》，同步目录后会显示到公开网站。`);
    } catch (error) {
      setText(addBookStatus, error.message || "添加失败。");
    } finally {
      if (submit) submit.disabled = false;
    }
  });

  bookSearch?.addEventListener("input", () => {
    renderBookResults().catch((error) => setText(bookStatus, error.message || "搜索失败。"));
  });

  addCategoryButton?.addEventListener("click", () => {
    const category = ensureCategoryOption(newCategoryInput?.value);
    if (!category) {
      setText(bookStatus, "请输入要新增的分类名称。");
      return;
    }
    setSelectedCategories([...selectedCategories(), category.id]);
    if (newCategoryInput) newCategoryInput.value = "";
    setText(bookStatus, `已加入分类：${category.name}`);
  });

  bookForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(bookForm).entries());
    const bookId = payload.id;
    delete payload.id;
    const categories = normalizeCategories(selectedCategories());
    const tags = splitList(payload.tags);
    if (!categories.length) {
      setText(bookStatus, "请至少填写一个分类。");
      return;
    }
    if (!tags.length) {
      setText(bookStatus, "请至少填写一个标签。");
      return;
    }
    payload.categories = categories;
    payload.category = categories[0];
    payload.tags = tags;
    try {
      setText(bookStatus, "正在保存……");
      const data = await requestAdmin(`/admin/books/${encodeURIComponent(bookId)}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      applySavedBook(bookId, data.item);
      setText(bookStatus, "已保存到后台，正在同步公开列表……");
      await renderBookResults();
      setStatusWithPublicLink(bookStatus, "已保存并上线。公开页面刷新后即可看到最新资料。", bookId);
    } catch (error) {
      setText(bookStatus, error.message || "保存失败。");
    }
  });
})();
