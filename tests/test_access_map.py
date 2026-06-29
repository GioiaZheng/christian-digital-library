from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_access_map", ROOT / "scripts" / "build_access_map.py"
)
assert SPEC and SPEC.loader
ACCESS_MAP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ACCESS_MAP
SPEC.loader.exec_module(ACCESS_MAP)


class AccessMapTests(unittest.TestCase):
    def test_build_access_map_keeps_raw_paths_out_of_public_site_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mapping = Path(directory) / "mapping.csv"
            with mapping.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["id", "object_key", "clean_title"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": "cdl-000001",
                        "object_key": "raw/测试.zip",
                        "clean_title": "测试书目",
                    }
                )
                writer.writerow(
                    {
                        "id": "cdl-000002",
                        "object_key": "covers/cdl-000002.jpg",
                        "clean_title": "不应进入",
                    }
                )

            access_map = ACCESS_MAP.build_access_map(mapping)

        self.assertIn("cdl-000001", access_map["books"])
        self.assertNotIn("cdl-000002", access_map["books"])
        self.assertEqual("raw/测试.zip", access_map["books"]["cdl-000001"]["key"])

    def test_cli_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mapping = Path(directory) / "mapping.csv"
            output = Path(directory) / "access-map.json"
            mapping.write_text(
                "id,object_key,clean_title\ncdl-000001,raw/book.zip,Book\n",
                encoding="utf-8",
            )

            ACCESS_MAP.main_from_args = getattr(ACCESS_MAP, "main", None)
            result = ACCESS_MAP.build_access_map(mapping)
            output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

            saved = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual("raw/book.zip", saved["books"]["cdl-000001"]["key"])


if __name__ == "__main__":
    unittest.main()
