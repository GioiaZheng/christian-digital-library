from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "preview-assets.js"
UPLOAD_WORKER = ROOT / "workers" / "upload-request.js"


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
        self.assertNotIn(".list(", source)

    def test_upload_worker_requires_upload_code_secret(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertIn("upload_code", source)
        self.assertIn("env.UPLOAD_CODE", source)
        self.assertIn("上传码不正确", source)
        public_config = (ROOT / "public" / "assets" / "upload-config.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("UPLOAD_CODE", public_config)

    def test_upload_worker_does_not_publish_catalog_or_raw_paths(self) -> None:
        source = UPLOAD_WORKER.read_text(encoding="utf-8")
        self.assertNotIn("data/books.csv", source)
        self.assertNotIn("raw/", source)
        self.assertNotIn("covers/", source)
        self.assertNotIn("previews/", source)


if __name__ == "__main__":
    unittest.main()
