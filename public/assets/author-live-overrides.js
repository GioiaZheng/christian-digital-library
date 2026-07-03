(() => {
  const profile = document.querySelector("[data-author-profile-name]");
  if (!profile) return;

  const authorName = String(profile.dataset.authorProfileName || "").trim();
  const bio = profile.querySelector("[data-author-profile-bio]");
  if (!authorName || !bio) return;

  const start = async () => {
    const authorBio = await window.CDL_CATALOG_OVERRIDES?.getAuthorBio?.(authorName);
    if (authorBio) bio.textContent = authorBio;
  };

  start().catch((error) => console.warn("作者资料暂时无法读取。", error));
})();
