from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "preview-assets.js"


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


if __name__ == "__main__":
    unittest.main()
