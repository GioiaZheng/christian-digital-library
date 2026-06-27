from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_repository", ROOT / "scripts" / "check_repository.py"
)
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class RepositoryPolicyTests(unittest.TestCase):
    def test_prohibited_book_format_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            book = Path(directory) / "示例书籍.ZIP"
            book.write_bytes(b"test")
            violations = CHECKER.find_violations([book])
            self.assertTrue(any("禁止格式" in item for item in violations))

    def test_oversized_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "large.bin"
            artifact.write_bytes(b"12345")
            violations = CHECKER.find_violations([artifact], max_size=4)
            self.assertTrue(any("文件过大" in item for item in violations))

    def test_small_source_file_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.py"
            source.write_text("print('ok')", encoding="utf-8")
            self.assertEqual([], CHECKER.find_violations([source]))


if __name__ == "__main__":
    unittest.main()
