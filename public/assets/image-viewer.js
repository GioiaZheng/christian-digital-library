(() => {
  const triggers = Array.from(document.querySelectorAll("[data-media-viewer-item]"));
  if (!triggers.length) return;

  const groups = new Map();
  const state = {
    items: [],
    index: 0,
    lastFocus: null,
    touchStartX: 0,
    touchStartY: 0,
  };

  const getCaption = (trigger) =>
    trigger.dataset.mediaCaption ||
    trigger.querySelector("img")?.getAttribute("alt") ||
    "图片预览";

  for (const trigger of triggers) {
    const group = trigger.dataset.mediaGroup || "default";
    const item = {
      src: trigger.dataset.mediaSrc || trigger.querySelector("img")?.currentSrc || "",
      caption: getCaption(trigger),
      trigger,
    };
    if (!item.src) continue;
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(item);
    trigger.dataset.mediaIndex = String(groups.get(group).length - 1);
    trigger.dataset.mediaGroup = group;
  }

  const viewer = document.createElement("div");
  viewer.className = "image-viewer";
  viewer.setAttribute("role", "dialog");
  viewer.setAttribute("aria-modal", "true");
  viewer.setAttribute("aria-label", "图片预览");
  viewer.innerHTML = `
    <div class="image-viewer-top">
      <div class="image-viewer-title" data-image-viewer-title></div>
      <button class="image-viewer-button" type="button" data-image-viewer-close aria-label="关闭">×</button>
    </div>
    <div class="image-viewer-stage" data-image-viewer-stage>
      <button class="image-viewer-button image-viewer-nav image-viewer-prev" type="button" data-image-viewer-prev aria-label="上一页">‹</button>
      <img class="image-viewer-image" data-image-viewer-image alt="">
      <button class="image-viewer-button image-viewer-nav image-viewer-next" type="button" data-image-viewer-next aria-label="下一页">›</button>
    </div>
    <div class="image-viewer-bottom">
      <span data-image-viewer-counter></span>
    </div>
  `;
  document.body.appendChild(viewer);

  const title = viewer.querySelector("[data-image-viewer-title]");
  const image = viewer.querySelector("[data-image-viewer-image]");
  const counter = viewer.querySelector("[data-image-viewer-counter]");
  const closeButton = viewer.querySelector("[data-image-viewer-close]");
  const prevButton = viewer.querySelector("[data-image-viewer-prev]");
  const nextButton = viewer.querySelector("[data-image-viewer-next]");
  const stage = viewer.querySelector("[data-image-viewer-stage]");

  const update = () => {
    const item = state.items[state.index];
    if (!item) return;

    image.src = item.src;
    image.alt = item.caption;
    title.textContent = item.caption;

    const hasMany = state.items.length > 1;
    prevButton.disabled = !hasMany;
    nextButton.disabled = !hasMany;
    counter.textContent = hasMany
      ? `${state.index + 1} / ${state.items.length} · 左右切换`
      : "按 Esc 关闭";
  };

  const open = (items, index, trigger) => {
    state.items = items;
    state.index = index;
    state.lastFocus = trigger || document.activeElement;
    update();
    viewer.classList.add("is-open");
    document.body.classList.add("has-image-viewer");
    closeButton.focus({ preventScroll: true });
  };

  const close = () => {
    viewer.classList.remove("is-open");
    document.body.classList.remove("has-image-viewer");
    image.removeAttribute("src");
    state.lastFocus?.focus?.({ preventScroll: true });
  };

  const move = (step) => {
    if (state.items.length <= 1) return;
    state.index = (state.index + step + state.items.length) % state.items.length;
    update();
  };

  for (const trigger of triggers) {
    trigger.addEventListener("click", () => {
      const group = trigger.dataset.mediaGroup || "default";
      const items = groups.get(group) || [];
      const index = Number(trigger.dataset.mediaIndex || 0);
      open(items, index, trigger);
    });
  }

  closeButton.addEventListener("click", close);
  prevButton.addEventListener("click", () => move(-1));
  nextButton.addEventListener("click", () => move(1));

  viewer.addEventListener("click", (event) => {
    if (event.target === viewer) close();
  });

  stage.addEventListener("pointerdown", (event) => {
    state.touchStartX = event.clientX;
    state.touchStartY = event.clientY;
  });

  stage.addEventListener("pointerup", (event) => {
    const deltaX = event.clientX - state.touchStartX;
    const deltaY = event.clientY - state.touchStartY;
    if (Math.abs(deltaX) < 42 || Math.abs(deltaX) < Math.abs(deltaY)) return;
    move(deltaX < 0 ? 1 : -1);
  });

  document.addEventListener("keydown", (event) => {
    if (!viewer.classList.contains("is-open")) return;
    if (event.key === "Escape") close();
    if (event.key === "ArrowLeft") move(-1);
    if (event.key === "ArrowRight") move(1);
  });
})();
