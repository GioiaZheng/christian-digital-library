from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ALLOWED_EXTENSIONS = {".zip", ".pdf", ".epub", ".mobi"}


def valid_file_key(value: str) -> bool:
    path = Path(value)
    return value.startswith("raw/") and path.suffix.lower() in ALLOWED_EXTENSIONS


def build_access_map(mapping_path: Path) -> dict[str, object]:
    books: dict[str, dict[str, str]] = {}
    with mapping_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            book_id = str(row.get("id") or "").strip()
            object_key = str(row.get("object_key") or "").strip()
            title = str(row.get("clean_title") or book_id).strip()
            if not book_id or not valid_file_key(object_key):
                continue
            books[book_id] = {
                "key": object_key,
                "title": title or book_id,
            }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "books": books,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="从私有 mapping 生成 R2 下载访问映射。")
    parser.add_argument("--mapping", type=Path, required=True, help="私有 public_catalog_mapping.csv 路径")
    parser.add_argument("--output", type=Path, required=True, help="输出 access-map.json 路径")
    args = parser.parse_args()

    access_map = build_access_map(args.mapping)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(access_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"生成完成：{len(access_map['books'])} 条访问映射。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
