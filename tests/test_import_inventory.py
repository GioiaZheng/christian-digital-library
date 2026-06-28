from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "import_inventory", ROOT / "scripts" / "import_inventory.py"
)
assert SPEC and SPEC.loader
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


class InventoryImportTests(unittest.TestCase):
    def test_messy_filename_is_cleaned(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/《示例恩典论》【英】示例作者 著【288页】.zip"
        )
        self.assertEqual("示例恩典论", title)
        self.assertEqual("示例作者", author)

    def test_series_title_is_not_mistaken_for_author(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/《07示例圣经注释-示例书卷》.zip"
        )
        self.assertEqual("07示例圣经注释-示例书卷", title)
        self.assertEqual("", author)

    def test_numeric_volume_is_kept_in_title(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/《示例对话-1》.zip")
        self.assertEqual("示例对话 1", title)
        self.assertEqual("", author)

    def test_trailing_catalog_number_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/示例教育文选_12403114.zip"
        )
        self.assertEqual("示例教育文选", title)
        self.assertEqual("", author)

    def test_leading_numeric_colon_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/2：在约伯的天平上.zip")
        self.assertEqual("在约伯的天平上", title)
        self.assertEqual("", author)

    def test_book_title_quotes_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/“自然之書”讀解：科學詮釋學.zip")
        self.assertEqual("自然之書讀解：科學詮釋學", title)
        self.assertEqual("", author)

    def test_ids_survive_object_rename_with_same_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "inventory.json"
            mapping = root / "mapping.csv"
            output = root / "books.csv"
            inventory.write_text(
                json.dumps(
                    [{"key": "incoming/旧名.zip", "size": 10, "etag": "same"}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            IMPORTER.import_inventory(inventory, mapping, output)
            with output.open(encoding="utf-8") as handle:
                first_id = next(csv.DictReader(handle))["id"]

            inventory.write_text(
                json.dumps(
                    [{"key": "incoming/新名.zip", "size": 10, "etag": "same"}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            IMPORTER.import_inventory(inventory, mapping, output)
            with output.open(encoding="utf-8") as handle:
                second_id = next(csv.DictReader(handle))["id"]
            self.assertEqual(first_id, second_id)

    def test_public_csv_contains_no_internal_object_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "inventory.json"
            mapping = root / "mapping.csv"
            output = root / "books.csv"
            inventory.write_text(
                json.dumps(
                    [
                        {
                            "key": "incoming/《示例书卷注释》示例作者.zip",
                            "size": 10,
                            "etag": "sample",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            IMPORTER.import_inventory(inventory, mapping, output)
            with output.open(encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(set(IMPORTER.BOOK_FIELDS), set(row))
            self.assertNotIn("incoming/", output.read_text(encoding="utf-8"))
            self.assertEqual("bible-study", row["category"])


if __name__ == "__main__":
    unittest.main()
