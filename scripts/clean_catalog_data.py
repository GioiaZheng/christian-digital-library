#!/usr/bin/env python3
"""清理公开书目里可以稳定判断的脏数据。

这个脚本只处理明显的格式错误：文件编号、排版字样、误拆的作者字段等。
不确定的作者、年份、出版社不在这里猜。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOKS = ROOT / "data" / "books.csv"

FORMAT_NOISE_RE = re.compile(r"\s*(?:单排版|双排版)\s*$")

BIBLE_STUDY_HINTS = (
    "圣经",
    "旧约",
    "新约",
    "列王记",
    "先知书",
    "罗马书",
    "注释",
    "研经",
)


def normalize_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r"\s*[（(]\s*(?:单排版|双排版)\s*[）)]\s*$", "", title)
    title = FORMAT_NOISE_RE.sub("", title)
    title = re.sub(r"^\d{1,3}\s+\d{1,3}[.．]?\s*(?=[\u3400-\u9fff])", "", title)
    title = re.sub(r"\s+", " ", title).strip(" ：:")
    return title


def normalize_person_field(value: str) -> str:
    value = value.strip()
    if value in {"单排版", "双排版", "修订版", "电子修订版"}:
        return ""
    value = FORMAT_NOISE_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip(" ：:")


def infer_category(title: str, current: str) -> str:
    if current and current != "other":
        return current
    if any(hint in title for hint in BIBLE_STUDY_HINTS):
        return "bible-study"
    if "尽心认识神" in title or "神的旨意" in title:
        return "spiritual-life"
    return current or "other"


def clean_row(row: dict[str, str]) -> bool:
    before = dict(row)
    title = row.get("clean_title", "")
    author = row.get("author", "")

    # 文件名 “... PARENT-ING TIME” 被分隔符误拆成了标题和作者。
    if title.endswith("PARENT") and author == "ING TIME":
        row["clean_title"] = f"{title}-ING TIME"
        row["author"] = ""

    # 中英并列文件名误把英文题名放进标题，中文题名和作者塞进 author。
    if row.get("id") == "cdl-005079":
        row["clean_title"] = "我能知道神的旨意吗"
        row["author"] = "司布尔"

    volume_noise = re.match(r"^([一二三四五六七八九十壹贰叁]+册)\s*电子修订版$", row.get("author", "").strip())
    if volume_noise:
        volume = volume_noise.group(1)
        if volume not in row.get("clean_title", ""):
            row["clean_title"] = f"{row.get('clean_title', '').strip()}（{volume}）"
        row["author"] = ""

    row["clean_title"] = normalize_title(row.get("clean_title", ""))
    for field in ("author", "translator"):
        if field in row:
            row[field] = normalize_person_field(row.get(field, ""))

    row["category"] = infer_category(row["clean_title"], row.get("category", ""))

    tags = [tag for tag in re.split(r"[;；]", row.get("tags", "")) if tag.strip()]
    if row["category"] == "bible-study":
        for hint in ("圣经", "注释", "研经"):
            if hint in row["clean_title"] and hint not in tags:
                tags.append(hint)
    row["tags"] = ";".join(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))

    return row != before


def clean_books(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    changed = 0
    for row in rows:
        if clean_row(row):
            changed += 1

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return changed


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="清理公开书目 CSV 中明显的格式错误")
    parser.add_argument("--books", type=Path, default=DEFAULT_BOOKS)
    args = parser.parse_args()
    changed = clean_books(args.books)
    print(f"已清理 {changed} 条书目。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
