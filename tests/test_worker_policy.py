from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "preview-assets.js"
UPLOAD_WORKER = ROOT / "workers" / "upload-request.js"
ACCESS_WORKER = ROOT / "workers" / "access-request.js"


class WorkerPolicyTests(unittest.TestCase):
    def test_worker_only_uses_read_access(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn("env.BOOK_ASSETS.get", source)
        self.assertNotIn(".put(", source)
        self.assertNotIn(".delete(", source)
        self.assertNotIn(".list(", source)

    def test_worker_restricts_asset_paths(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn(r"^covers\/cdl-\d+\.jpg$", source)
        self.assertIn(r"^previews\/cdl-\d+\/page-[1-9]\d*\.jpg$", source)
        self.assertIn("if (!key) return notFound()", source)

    def test_worker_does_not_mention_original_file_prefix(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        self.assertNotIn("raw/", source)
        self.assertNotIn(".zip", source)

    def test_upload_worker_writes_only_pending_objects(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn("pending/uploads/", source)
        self.assertIn("pending/metadata/", source)
        self.assertIn("status: \"pending\"", source)
        self.assertIn("env.BOOK_UPLOADS.put", source)
        self.assertNotIn(".delete(", source)

    def test_upload_form_no_longer_requires_public_submit_code(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertNotIn("upload_code", source)
        self.assertNotIn("UPLOAD_CODE", source)
        public_config = (ROOT / "public" / "assets" / "upload-config.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("UPLOAD_CODE", public_config)
        self.assertNotIn("upload_code", public_config)

    def test_upload_worker_returns_json_for_bad_form_data(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn("request.formData().catch(() => null)", source)
        self.assertIn("请填写书名、作者并选择文件。", source)

    def test_admin_worker_requires_separate_admin_secret(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn("env.ADMIN_CODE", source)
        self.assertIn("X-CDL-Admin-Code", source)
        self.assertIn("管理员密码不正确", source)
        public_config = (ROOT / "public" / "assets" / "admin-config.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ADMIN_CODE", public_config)
        self.assertNotIn("ACCESS_CODE", public_config)

    def test_upload_worker_keeps_admin_actions_out_of_public_catalog(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertNotIn("data/books.csv", source)
        self.assertNotIn("covers/", source)
        self.assertNotIn("previews/", source)
        self.assertIn("metadata/admin-overrides/", source)
        self.assertIn("files/admin-approved/", source)
        self.assertNotIn("raw/admin-approved/", source)

    def test_upload_worker_rejects_zip_for_new_uploads(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn('new Set(["pdf", "epub", "mobi"])', source)
        self.assertNotIn('"zip"', source)
        self.assertIn("不要上传 ZIP", source)
        self.assertIn("MAX_UPLOAD_BYTES", source)

    def test_admin_worker_supports_direct_book_add(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn("files/admin-added/", source)
        self.assertIn("metadata/admin-added/", source)
        self.assertIn('pathname.endsWith("/admin/books")', source)
        self.assertIn('status: "admin_added"', source)
        self.assertIn("file.size > maxBytes", source)

    def test_admin_worker_supports_private_reading_status(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn("metadata/admin-reading-status.json", source)
        self.assertIn("/admin/reading-status", source)
        self.assertIn("/reading-status", source)
        self.assertIn("want_to_read", source)
        self.assertIn("finished", source)
        self.assertIn("阅读状态不正确", source)

    def test_admin_book_override_requires_multiple_categories_and_tags(self) -> None:
        worker_source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn("function cleanList", worker_source)
        self.assertIn("const categories = cleanList", worker_source)
        self.assertIn("const tags = cleanList", worker_source)
        self.assertIn("请至少填写一个分类", worker_source)
        self.assertIn("请至少填写一个标签", worker_source)
        self.assertIn("category: categories[0]", worker_source)
        self.assertIn("categories,", worker_source)

        admin_source = (ROOT / "public" / "assets" / "admin.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("const splitList", admin_source)
        self.assertIn('namedItem("categories")', admin_source)
        self.assertIn("payload.categories = categories", admin_source)
        self.assertIn("payload.tags = tags", admin_source)

    def test_access_worker_requires_secret_and_private_map(self) -> None:
        source = ACCESS_WORKER.read_text(encoding="utf-8")
        self.assertIn("env.ACCESS_CODE", source)
        self.assertIn("metadata/access-map.json", source)
        self.assertIn("env.BOOK_FILES.get", source)
        self.assertIn("access_action", source)
        self.assertIn("READER_TOKEN_SECRET", source)
        self.assertIn("reader/${bookId}/manifest.json", source)
        self.assertIn("reader_url", source)
        self.assertIn("X-CDL-File-Extension", source)
        self.assertIn("访问码不正确", source)
        self.assertNotIn(".put(", source)
        self.assertNotIn(".delete(", source)
        self.assertNotIn(".list(", source)

    def test_access_js_supports_download_and_online_reading(self) -> None:
        source = (ROOT / "public" / "assets" / "access.js").read_text(encoding="utf-8")
        self.assertIn('value === "read"', source)
        self.assertIn("reader_url", source)
        self.assertIn("window.open", source)
        self.assertIn("downloadBlob", source)
        self.assertNotIn("DecompressionStream", source)
        self.assertNotIn("parseZipEntries", source)
        self.assertNotIn("ACCESS_CODE", source)
        self.assertNotIn("raw/", source)

    def test_reader_page_lazy_loads_reader_images(self) -> None:
        reader_page = (ROOT / "public" / "reader.html").read_text(encoding="utf-8")
        reader_js = (ROOT / "public" / "assets" / "reader.js").read_text(encoding="utf-8")
        self.assertIn("assets/reader.js", reader_page)
        self.assertIn("page-${paddedPage(index)}", reader_js)
        self.assertIn('image.loading = index <= 2 ? "eager" : "lazy"', reader_js)
        self.assertIn("data-reader-zoom-in", reader_page)
        self.assertIn("--reader-zoom", reader_js)
        self.assertNotIn("ACCESS_CODE", reader_js)
        self.assertNotIn("raw/", reader_js)

    def test_image_viewer_supports_preview_navigation(self) -> None:
        source = (ROOT / "public" / "assets" / "image-viewer.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("data-media-viewer-item", source)
        self.assertIn("ArrowLeft", source)
        self.assertIn("ArrowRight", source)
        self.assertIn("pointerup", source)
        self.assertIn("data-image-viewer-zoom-in", source)
        self.assertIn("translate3d(${state.panX}px, ${state.panY}px, 0) scale", source)
        self.assertIn("setPointerCapture", source)
        self.assertIn("is-pannable", source)
        self.assertIn("event.target === stage", source)
        self.assertNotIn("ACCESS_CODE", source)
        self.assertNotIn("raw/", source)

    def test_public_access_config_has_no_secret_or_raw_path(self) -> None:
        public_config = (ROOT / "public" / "assets" / "access-config.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ACCESS_CODE", public_config)
        self.assertNotIn("access_code", public_config)
        self.assertNotIn("raw/", public_config)


if __name__ == "__main__":
    unittest.main()
