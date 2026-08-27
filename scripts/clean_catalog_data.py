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
NIVAC_PREFIX_RE = re.compile(r"^NIVAC\s*(?=国际释经应用系列)", re.IGNORECASE)
NIVAC_TAIL_RE = re.compile(r"NIVAC(?:\+[A-Za-z]+)?\+?$", re.IGNORECASE)

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

CHINESE_VOLUME_NUMERALS = {
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
    "10": "十",
}

TAG_ALIASES = {
    "聖經": "圣经", "舊約": "旧约", "新約": "新约", "註釋": "注释", "釋經": "释经", "研經": "研经",
    "創世記": "创世记", "出埃及記": "出埃及记", "利未記": "利未记", "民數記": "民数记",
    "申命記": "申命记", "詩篇": "诗篇", "傳道書": "传道书", "啟示錄": "启示录",
    "羅馬書": "罗马书", "約翰福音": "约翰福音", "使徒行傳": "使徒行传",
    "歷史": "历史", "聖靈": "圣灵", "歌羅西": "歌罗西书", "馬太福音": "马太福音",
    "馬可福音": "马可福音", "解經": "解经", "傳福音": "传福音", "傳道": "传道",
    "古蘭經": "古兰经", "聖經輔導": "圣经辅导", "加拉太": "加拉太书",
    "以弗所": "以弗所书", "腓立比": "腓立比书", "歌罗西": "歌罗西书",
}

BIBLE_BOOK_TAGS = {
    "创世记": "旧约", "出埃及记": "旧约", "利未记": "旧约", "民数记": "旧约", "申命记": "旧约",
    "约书亚记": "旧约", "士师记": "旧约", "路得记": "旧约", "撒母耳记": "旧约", "列王纪": "旧约",
    "历代志": "旧约", "以斯拉记": "旧约", "尼希米记": "旧约", "以斯帖记": "旧约", "约伯记": "旧约",
    "诗篇": "旧约", "箴言": "旧约", "传道书": "旧约", "雅歌": "旧约", "以赛亚书": "旧约",
    "耶利米书": "旧约", "耶利米哀歌": "旧约", "以西结书": "旧约", "但以理书": "旧约", "何西阿书": "旧约",
    "约珥书": "旧约", "阿摩司书": "旧约", "俄巴底亚书": "旧约", "约拿书": "旧约", "弥迦书": "旧约",
    "那鸿书": "旧约", "哈巴谷书": "旧约", "西番雅书": "旧约", "哈该书": "旧约", "撒迦利亚书": "旧约",
    "玛拉基书": "旧约", "马太福音": "新约", "马可福音": "新约", "路加福音": "新约", "约翰福音": "新约",
    "使徒行传": "新约", "罗马书": "新约", "哥林多前书": "新约", "哥林多后书": "新约", "加拉太书": "新约",
    "以弗所书": "新约", "腓立比书": "新约", "歌罗西书": "新约", "帖撒罗尼迦前书": "新约", "帖撒罗尼迦后书": "新约",
    "提摩太前书": "新约", "提摩太后书": "新约", "提多书": "新约", "腓利门书": "新约", "希伯来书": "新约",
    "雅各书": "新约", "彼得前书": "新约", "彼得后书": "新约", "约翰一书": "新约", "约翰二书": "新约",
    "约翰三书": "新约", "犹大书": "新约", "启示录": "新约",
}

SUBJECT_TAG_HINTS = {
    "末世论": ("末世论",), "终末论": ("末世论",), "圣经神学": ("圣经神学",),
    "系统神学": ("系统神学",), "教义学": ("教义学",), "护教学": ("护教学",),
    "基督教伦理": ("基督教伦理",), "伦理学": ("伦理学",), "教会史": ("教会史",),
    "基督教史": ("基督教史",), "景教": ("景教", "中国基督教史"), "宗教改革": ("宗教改革",),
    "东正教": ("东正教",), "灵修": ("灵修",), "祷告": ("祷告",), "门徒": ("门徒训练",),
    "婚姻": ("婚姻",), "家庭": ("家庭",), "辅导": ("辅导",), "宣教": ("宣教",),
    "讲道": ("讲道",), "释经": ("释经",), "研经": ("研经",), "注释": ("注释",),
    "无误": ("圣经无误",), "默示": ("圣经默示",), "三一": ("三一论",),
    "基督论": ("基督论",), "救恩": ("救恩论",), "称义": ("称义",), "圣灵": ("圣灵论",),
    "教会论": ("教会论",), "创造": ("创造论",), "罪论": ("罪论",),
    "巴特": ("卡尔·巴特",), "祁克果": ("祁克果",), "加尔文": ("加尔文",), "路德": ("马丁·路德",),
}

OVERLY_GENERIC_TAGS = {"其他", "待核实", "书名待核", "作者待核", "基督教"}


def split_title_author_suffix(title: str) -> tuple[str, str] | None:
    """处理“书名：作者：2”这类从文件名导入来的重复尾巴。"""
    parts = [part.strip() for part in re.split(r"[：:]", title) if part.strip()]
    if len(parts) < 3 or not parts[-1].isdigit():
        return None
    author = parts[-2]
    if len(author) > 12 or re.search(r"[A-Za-z0-9]", author):
        return None
    clean_title = "：".join(parts[:-2]).strip()
    if not clean_title:
        return None
    return clean_title, author


def normalize_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r"^NIVAC\+\s*[（(]\s*(?P<title>.+?)\s*[）)]$", r"国际释经应用系列：\g<title>", title, flags=re.IGNORECASE)
    title = re.sub(r"^NIVAC\s+(?P<title>.+)$", r"\g<title>", title, flags=re.IGNORECASE)
    title = title.replace("帖前后注释", "帖撒罗尼迦前后书注释")
    title = re.sub(r"\s*[（(]\s*(?:单排版|双排版)\s*[）)]\s*$", "", title)
    title = FORMAT_NOISE_RE.sub("", title)
    title = NIVAC_PREFIX_RE.sub("", title)
    title = NIVAC_TAIL_RE.sub("", title).strip()
    title = re.sub(r"^\d{1,3}\s+\d{1,3}[.．]?\s*(?=[\u3400-\u9fff])", "", title)
    title = re.sub(r"^\d{1,3}\s*(?=分辨真伪)", "", title)
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

def normalize_tags(title: str, current_tags: str) -> str:
    """统一标签写法，并从题名补充可以确定的主题。"""
    tags = []
    for raw_tag in re.split(r"[;；,，]", current_tags):
        tag = TAG_ALIASES.get(raw_tag.strip(), raw_tag.strip())
        if tag and tag not in OVERLY_GENERIC_TAGS and tag not in tags:
            tags.append(tag)

    normalized_title = title
    for old_tag, new_tag in TAG_ALIASES.items():
        normalized_title = normalized_title.replace(old_tag, new_tag)

    for book, testament in BIBLE_BOOK_TAGS.items():
        if book in normalized_title:
            for tag in (book, testament):
                if tag not in tags:
                    tags.append(tag)

    for hint, inferred_tags in SUBJECT_TAG_HINTS.items():
        if hint in normalized_title:
            for tag in inferred_tags:
                if tag not in tags:
                    tags.append(tag)

    if len(tags) > 1:
        tags = [tag for tag in tags if tag not in {"基督", "神学", "圣经"}]

    return ";".join(tags)


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

    # 明显的字段错位：作者名进了书名，英文副题和中文书名进了作者栏。
    if row.get("id") == "cdl-001567":
        row["clean_title"] = "你的恩赐知多少"
        row["author"] = "马有藻"

    if row.get("id") in {"cdl-004185", "cdl-004186"} and row.get("author", "").strip() == "地狱来鸿":
        row["clean_title"] = "地狱来鸿"
        row["author"] = "C.S.路易斯"

    if row.get("id") == "cdl-004384" and row.get("author", "").strip() == "基督教要义":
        row["clean_title"] = "基督教要义（三联旧版，上中下合集）"
        row["author"] = "约翰·加尔文"

    if row.get("id") == "cdl-006727":
        row["clean_title"] = "雅各书学习指南"

    # 文件名前缀把分类塞进标题。
    church_history = re.match(r"^教会历史[-－—](?P<title>.+?)[-－—](?P<volume>\d+)$", row.get("clean_title", "").strip())
    if church_history:
        volume = CHINESE_VOLUME_NUMERALS.get(church_history.group("volume"), church_history.group("volume"))
        row["clean_title"] = f"{church_history.group('title')}（{volume}）"
        row["category"] = "church-history"

    # 文件名尾部的“：作者：2”是撞名编号，不是书名的一部分。
    title_author = split_title_author_suffix(row.get("clean_title", ""))
    if title_author and not row.get("author", "").strip():
        row["clean_title"], row["author"] = title_author

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
    row["tags"] = normalize_tags(row["clean_title"], ";".join(tags))

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

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
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
