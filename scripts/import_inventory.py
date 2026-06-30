#!/usr/bin/env python3
"""将私有存储清单转换为不含内部路径的公开书目 CSV。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
BOOK_FIELDS = [
    "id",
    "clean_title",
    "author",
    "publisher",
    "year",
    "language",
    "category",
    "tags",
    "description",
    "table_of_contents",
    "cover_image_url",
    "preview_page_count",
    "preview_base_url",
    "access_required",
    "access_url",
    "copyright_status",
    "can_public_download",
]
MAPPING_FIELDS = [
    "id",
    "object_key",
    "size",
    "etag",
    "clean_title",
    "author",
    "category",
    "reviewed",
]

UNKNOWN_AUTHOR_WORDS = {
    "麦种",
    "麦种出版",
    "麦种彩色版",
    "麦种传道会",
    "美国麦种传道会",
    "环球新本",
    "校园",
    "华神",
    "天道",
    "好书",
    "完整版",
    "非完整版",
    "repaired",
}
TYNDALE_COMMENTARY_PATTERN = r"丁道尔(?:新约|旧约)(?:圣经)?注释"
MAIZHONG_COMMENTARY = "麦种圣经注释"
MAIZHONG_SOURCE_LABELS = {
    "麦种",
    "麦种出版",
    "麦种彩色版",
    "麦种传道会",
    "美国麦种传道会",
}
CATALOG_PREFIX_TOPICS = (
    "校园",
    "旧约",
    "舊約",
    "新约",
    "新約",
    "新旧约",
    "新舊約",
    "创世纪",
    "創世紀",
    "创世记",
    "創世記",
    "教牧",
    "古代基督",
    "圣经",
    "聖經",
    "漂亮",
    "随时候命",
    "隨時候命",
    "仁者无惧",
    "仁者無懼",
    "先知书",
    "先知書",
    "回归义路",
    "回歸義路",
    "对观福音",
    "對觀福音",
    "得胜凯歌",
    "得勝凱歌",
    "效忠基督",
    "拉尼斯",
    "篇以",
    "歌林多",
    "哥林多",
    "剑桥基督教史",
)
TIANDAO_COMMENTARY_PATTERN = r"天道(?:圣经|聖經)?(?:注|註)(?:释|釋)"
BIBLE_SERIES_LABELS = (
    "圣经信息系列",
    "聖經信息系列",
    "生命信息系列",
    "天道研经",
    "天道研經",
    "天道研经导读",
    "天道研經導讀",
)
NON_AUTHOR_WORDS = (
    "圣经",
    "聖經",
    "注释",
    "註釋",
    "神学",
    "神學",
    "教会",
    "教會",
    "福音",
    "课程",
    "課程",
    "指南",
    "系列",
    "阅读",
    "閱讀",
    "精选",
    "精選",
    "书",
    "書",
    "记",
    "記",
    "传",
    "傳",
    "学",
    "學",
    "主义",
    "主義",
    "思想",
    "信念",
    "生活",
    "秘诀",
    "秘訣",
    "真理",
    "世界",
    "人生",
    "时代",
    "時代",
    "原则",
    "原則",
    "方法",
    "道路",
    "艺术",
    "藝術",
    "灵魂",
    "靈魂",
    "圣灵",
    "聖靈",
    "异象",
    "異象",
    "呼召",
    "彼犹",
    "赞美",
    "讚美",
    "心语",
    "心語",
    "简释",
    "簡釋",
    "字字珠玑",
    "字字珠璣",
    "材料",
    "导论",
    "導論",
    "出版",
    "时间",
    "時間",
    "诗篇",
    "詩篇",
    "讲章",
    "講章",
    "仁者无惧",
    "仁者無懼",
    "得胜凯歌",
    "得勝凱歌",
    "回归义路",
    "回歸義路",
    "效忠基督",
    "路加福音",
    "启示录",
    "啟示錄",
)

BIBLE_TITLE_PREFIX_WORDS = (
    "圣经信息系列",
    "聖經信息系列",
    "天道",
    "丁道尔",
    "丁道爾",
    "创世记",
    "創世記",
    "出埃及记",
    "出埃及記",
    "利未记",
    "利未記",
    "民数记",
    "民數記",
    "申命记",
    "申命記",
    "约书亚",
    "約書亞",
    "士师记",
    "士師記",
    "路得记",
    "路得記",
    "撒母耳",
    "列王纪",
    "列王記",
    "列王记",
    "历代志",
    "歷代志",
    "以斯拉",
    "尼希米",
    "以斯帖",
    "约伯",
    "約伯",
    "诗篇",
    "詩篇",
    "箴言",
    "传道书",
    "傳道書",
    "雅歌",
    "以赛亚",
    "以賽亞",
    "耶利米",
    "以西结",
    "以西結",
    "但以理",
    "何西阿",
    "约珥",
    "約珥",
    "阿摩司",
    "俄巴底亚",
    "俄巴底亞",
    "约拿",
    "約拿",
    "弥迦",
    "彌迦",
    "那鸿",
    "那鴻",
    "哈巴谷",
    "西番雅",
    "哈该",
    "哈該",
    "撒迦利亚",
    "撒迦利亞",
    "玛拉基",
    "瑪拉基",
    "马太",
    "馬太",
    "马可",
    "馬可",
    "路加",
    "约翰",
    "約翰",
    "使徒",
    "罗马书",
    "羅馬書",
    "哥林多",
    "加拉太",
    "以弗所",
    "腓立比",
    "歌罗西",
    "歌羅西",
    "帖撒罗尼迦",
    "帖撒羅尼迦",
    "提摩太",
    "提多",
    "腓利门",
    "腓利門",
    "希伯来",
    "希伯來",
    "雅各",
    "彼得",
    "犹大",
    "猶大",
    "启示录",
    "啟示錄",
)

CATEGORY_RULES = [
    ("reference", ("辞典", "詞典", "词典", "百科", "目录", "手册", "工具书", "索引")),
    (
        "bible-study",
        (
            "圣经",
            "聖經",
            "旧约",
            "舊約",
            "新约",
            "新約",
            "释经",
            "釋經",
            "解经",
            "解經",
            "研经",
            "研經",
            "注释",
            "註釋",
            "创世记",
            "創世記",
            "出埃及记",
            "出埃及記",
            "诗篇",
            "詩篇",
            "箴言",
            "约翰福音",
            "約翰福音",
            "罗马书",
            "羅馬書",
            "希伯来书",
            "希伯來書",
            "利未记",
            "利未記",
            "民数记",
            "民數記",
            "申命记",
            "申命記",
            "约书亚记",
            "約書亞記",
            "士师记",
            "士師記",
            "路得记",
            "路得記",
            "撒母耳",
            "列王纪",
            "列王記",
            "历代志",
            "歷代志",
            "以斯拉",
            "尼希米",
            "以斯帖",
            "约伯",
            "雅歌",
            "以赛亚",
            "以賽亞",
            "耶利米",
            "以西结",
            "以西結",
            "但以理",
            "何西阿",
            "约珥",
            "約珥",
            "阿摩司",
            "俄巴底亚",
            "約拿",
            "约拿",
            "弥迦",
            "彌迦",
            "那鸿",
            "那鴻",
            "哈巴谷",
            "西番雅",
            "哈该",
            "哈該",
            "撒迦利亚",
            "撒迦利亞",
            "玛拉基",
            "瑪拉基",
            "马太福音",
            "馬太福音",
            "马可福音",
            "馬可福音",
            "路加福音",
            "使徒行传",
            "使徒行傳",
            "哥林多",
            "加拉太",
            "以弗所",
            "腓立比",
            "歌罗西",
            "歌羅西",
            "帖撒罗尼迦",
            "帖撒羅尼迦",
            "提摩太",
            "提多书",
            "提多書",
            "腓利门",
            "腓利門",
            "雅各书",
            "雅各書",
            "彼得前",
            "彼得后",
            "彼得後",
            "约翰壹",
            "約翰壹",
            "启示录",
            "啟示錄",
        ),
    ),
    ("missions", ("宣教", "差传", "差傳", "传福音", "傳福音", "传道", "傳道", "傅道", "布道", "佈道", "穆斯林", "回教徒")),
    ("pastoral", ("讲道", "講道", "讲章", "講章", "牧会", "牧會", "牧养", "牧養", "教会治理", "教會治理", "辅导", "輔導", "事工", "教会成员", "教會成員")),
    ("family-ministry", ("婚姻", "家庭", "亲子", "親子", "儿童", "兒童", "孩子", "青少年", "早教")),
    (
        "church-history",
        (
            "教会史",
            "教會史",
            "宗教改革",
            "改教",
            "历史",
            "歷史",
            "传记",
            "傳記",
            "路德",
            "加尔文传",
            "加爾文傳",
            "奥古斯丁",
            "奧古斯丁",
            "简史",
            "簡史",
            "生平",
            "内地会",
            "內地會",
            "清教徒",
            "十字军",
            "十字軍",
            "威伯福斯",
            "朋霍费尔",
            "朋霍費爾",
            "马礼逊",
            "馬禮遜",
        ),
    ),
    (
        "theology",
        (
            "神学",
            "神學",
            "教义",
            "教義",
            "护教",
            "護教",
            "系统神学",
            "系統神學",
            "基督论",
            "基督論",
            "救赎",
            "救贖",
            "称义",
            "稱義",
            "改革宗",
            "加尔文主义",
            "加爾文主義",
        ),
    ),
    (
        "spiritual-life",
        (
            "灵修",
            "靈修",
            "祷告",
            "禱告",
            "门徒",
            "門徒",
            "圣洁",
            "聖潔",
            "敬拜",
            "属灵生活",
            "屬靈生活",
            "生命成长",
            "生命成長",
            "信心",
            "属灵",
            "屬靈",
            "灵性",
            "靈性",
            "灵命",
            "靈命",
            "与神",
            "與神",
            "与主",
            "與主",
            "主日",
            "赞美",
            "讚美",
            "祝福",
            "敬虔",
        ),
    ),
    (
        "theology",
        (
            "上帝",
            "三位一体",
            "三位一體",
            "十字架",
            "信经",
            "信經",
            "道成肉身",
            "救恩",
            "恩典",
            "基督",
            "圣灵",
            "聖靈",
            "信仰",
            "教会",
            "教會",
        ),
    ),
    (
        "culture-society",
        (
            "哲学",
            "哲學",
            "文化",
            "社会",
            "社會",
            "伦理",
            "倫理",
            "政治",
            "法律",
            "科学",
            "科學",
            "教育",
            "宗教",
        ),
    ),
]


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def remove_copy_markers(value: str) -> str:
    previous = ""
    while previous != value:
        previous = value
        value = re.sub(
            r"\s*(?:[（(\[]\d+[）)\]]|[-_ ]?copy(?:\s*\d+)?|[-_ ]?compressed)$",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()
    return value


def clean_person(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"^[\s_\-—:：]+", "", value)
    value = re.sub(r"^[【\[(](?:中|英|美|德|俄|澳|法)[】\])]", "", value)
    value = re.sub(r"【[^】]*(?:页|年|\d{4})[^】]*】", "", value)
    value = re.sub(r"(?:著(?!名|作|者)|着|主编|編著|编著|编|編|译|譯|牧师|牧師|博士)+", "", value)
    value = re.sub(r"(?:19|20)\d{2}(?:[.年]\d{1,2})?.*$", "", value)
    for word in UNKNOWN_AUTHOR_WORDS:
        value = re.sub(rf"(?:[\s_\-—]*{re.escape(word)})+$", "", value)
    value = re.sub(r"[《》【】\[\]()（）'\"`]+", " ", value)
    value = re.sub(r"[.,，:：·•—–_、-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def source_label(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"(?:19|20)\d{2}.*$", "", value)
    value = re.sub(r"[\s_\-—:：,，.。()（）]+", "", value)
    return value


def is_maizhong_source(value: str) -> bool:
    label = source_label(value)
    return label in MAIZHONG_SOURCE_LABELS


def looks_like_maizhong_author(value: str) -> bool:
    return looks_like_person(value) or clean_person(value) in {"唐书礼"}


def strip_catalog_code_prefix(value: str) -> str:
    value = normalize(value)
    topic_pattern = "|".join(map(re.escape, CATALOG_PREFIX_TOPICS))
    value = re.sub(r"^[Mm]\d{3,5}\s+", "", value)
    value = re.sub(r"^[RSYZ](?=[\u3400-\u9fff])", "", value)
    value = re.sub(r"^[xX]\d{1,3}(?=[\u3400-\u9fff])", "", value)
    value = re.sub(r"^\d{1,3}(?:\s*[+＋,，、]\s*\d{1,3})+\s*", "", value)
    value = re.sub(r"^(?:\d{1,3}\s*){2,}(?=古代基督)", "", value)
    value = re.sub(r"^(?:\d{1,3}\s+){2,}\d{1,3}\s*[-—:：]?\s*", "", value)
    value = re.sub(r"^\d{1,3}\s+(?=[\u3400-\u9fff])", "", value)
    value = re.sub(rf"^(?:\d{{1,3}}\s*[-_]\s*)?\d{{1,3}}\s*(?=(?:{topic_pattern}))", "", value)
    value = re.sub(r"^\d{1,3}\s+(?=古代基督)", "", value)
    return value.strip()


def split_filename_parts(value: str) -> list[str]:
    return [
        part.strip().strip("@")
        for part in re.split(r"\s*(?:--+|——+|[-_—－:：])\s*", value)
        if part.strip().strip("@")
    ]


def format_catalog_title(value: str) -> str:
    value = clean_title(value)
    if re.search(r"[A-Za-z]", value):
        return value
    parts = [part for part in value.split() if part]
    if 1 < len(parts) <= 3:
        return "：".join(parts)
    return value


def normalize_bible_series_title(value: str) -> str:
    value = clean_title(value)
    series_pattern = "|".join(map(re.escape, BIBLE_SERIES_LABELS))
    match = re.match(rf"^(?P<title>.+?)[（(](?P<series>{series_pattern})[）)]$", value)
    if match:
        return f"{match.group('series')}：{clean_title(match.group('title'))}"
    match = re.match(rf"^(?P<title>.+?)\s+(?P<series>{series_pattern})$", value)
    if match:
        return f"{match.group('series')}：{clean_title(match.group('title'))}"
    return value


def split_tail_author_from_catalog_title(value: str) -> tuple[str, str]:
    value = normalize(value)
    parenthetical = re.match(
        r"^(?P<title>.+?)\s+(?P<author>[\u3400-\u9fff·]{2,12})(?:[（(](?P<roman>[^）)]+)[）)])$",
        value,
    )
    if parenthetical:
        author = clean_person(
            f"{parenthetical.group('author')} {parenthetical.group('roman')}"
        )
        return format_catalog_title(parenthetical.group("title")), author

    english = re.match(r"^(?P<title>.+?)\s+(?P<author>[A-Z][A-Za-z.,'’\s]+)$", value)
    if english:
        return format_catalog_title(english.group("title")), clean_person(english.group("author"))

    chinese = re.match(r"^(?P<title>.+?)\s+(?P<author>[\u3400-\u9fff·]{2,12})(?:博士)?$", value)
    if chinese and looks_like_person(chinese.group("author")):
        return format_catalog_title(chinese.group("title")), clean_person(chinese.group("author"))

    return format_catalog_title(value), ""


def split_tiandao_parts(parts: list[str]) -> tuple[str, str] | None:
    for index, part in enumerate(parts):
        if not re.fullmatch(TIANDAO_COMMENTARY_PATTERN, part):
            continue
        title_parts = parts[:index]
        tail_parts = parts[index + 1 :]
        author = ""
        if tail_parts and looks_like_person(tail_parts[-1]):
            author = clean_person(tail_parts[-1])
        elif len(title_parts) >= 2 and looks_like_person(title_parts[-1]):
            author = clean_person(title_parts[-1])
            title_parts = title_parts[:-1]
        title = clean_title("：".join(title_parts))
        if title:
            return clean_title(f"{part}：{title}"), author
    return None


def normalize_series_parts(parts: list[str]) -> tuple[str, str] | None:
    if len(parts) < 2:
        return None

    for index, part in enumerate(parts):
        series = clean_title(part)
        if series not in BIBLE_SERIES_LABELS:
            continue

        author = ""
        if index == 0:
            title_parts = parts[1:]
            if title_parts and looks_like_person(title_parts[-1]):
                author = clean_person(title_parts[-1])
                title_parts = title_parts[:-1]
        else:
            title_parts = parts[:index]
            tail_parts = parts[index + 1 :]
            if tail_parts and looks_like_person(tail_parts[-1]):
                author = clean_person(tail_parts[-1])
            elif title_parts and looks_like_person(title_parts[-1]):
                author = clean_person(title_parts[-1])
                title_parts = title_parts[:-1]

        title = clean_title("：".join(title_parts))
        if title:
            return f"{series}：{title}", author

    return None


def split_alpha_volume_code_title_author(stem: str) -> tuple[str, str] | None:
    book_pattern = "|".join(
        map(re.escape, sorted(BIBLE_TITLE_PREFIX_WORDS, key=len, reverse=True))
    )
    match = re.match(
        rf"^\d{{1,2}}[A-Za-z]\s+(?P<book>{book_pattern})\s+"
        r"(?P<volume>上|下|上卷|下卷)\s+(?P<author>.+)$",
        normalize(stem),
    )
    if not match:
        return None
    author = clean_person(match.group("author"))
    title = clean_title(f"{match.group('book')}：{match.group('volume')}")
    return title, author


def split_catalog_code_title_author(stem: str) -> tuple[str, str] | None:
    alpha_volume = split_alpha_volume_code_title_author(stem)
    if alpha_volume:
        return alpha_volume

    cleaned = strip_catalog_code_prefix(stem.replace("@", ""))
    if cleaned == stem:
        return None

    if re.match(r"^古代基督信仰圣经注释(?:\s*[（(]|\s+)", cleaned):
        return clean_title(cleaned), ""

    parts = split_filename_parts(cleaned)
    while parts and source_label(parts[0]) in {"校园"}:
        parts.pop(0)
    if not parts:
        return clean_title(cleaned), ""

    tiandao = split_tiandao_parts(parts)
    if tiandao:
        return tiandao

    series_parts = normalize_series_parts(parts)
    if series_parts:
        return series_parts

    if len(parts) >= 2 and re.search(r"[\u3400-\u9fff]", parts[-1]):
        last_title, last_author = split_tail_author_from_catalog_title(parts[-1])
        if last_author:
            return normalize_bible_series_title("：".join([*parts[:-1], last_title])), last_author

    if len(parts) >= 2 and looks_like_person(parts[0]):
        return normalize_bible_series_title(parts[1]), clean_person(parts[0])

    if len(parts) >= 2 and looks_like_person(parts[-1]):
        author = clean_person(parts[-1])
        title = normalize_bible_series_title("：".join(parts[:-1]))
        return title, author

    if len(parts) > 1:
        return normalize_bible_series_title("：".join(parts)), ""

    title, author = split_tail_author_from_catalog_title(parts[0])
    return normalize_bible_series_title(title), author


def looks_like_person(value: str) -> bool:
    candidate = clean_person(value)
    if not candidate or candidate in UNKNOWN_AUTHOR_WORDS or len(candidate) > 28:
        return False
    if any(word in candidate for word in NON_AUTHOR_WORDS):
        return False
    if candidate.isdigit():
        return False
    if re.fullmatch(r"[\u3400-\u9fff ]{2,12}", candidate):
        return True
    return bool(re.fullmatch(r"[A-Za-z\u3400-\u9fff ]{3,28}", candidate))


def clean_title(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"\.(?:pdf|rar|epub|mobi)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"~?微信[:：]?[A-Za-z0-9_-]+.*$", "", value, flags=re.IGNORECASE)
    value = remove_copy_markers(value)
    value = re.sub(r"\s*[-_ ]?repaired\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^喜乐出版社[-—_:： ]+", "", value)
    value = re.sub(r"[（(]\s*(?:麦种|麦种出版|麦种彩色版|麦种传道会|美国麦种传道会)\s*[）)]", "", value)
    value = re.sub(r"\s*[-—_:： ]+(?:麦种|麦种出版|麦种彩色版|麦种传道会|美国麦种传道会)\s*$", "", value)
    value = re.sub(r"^[（(]\d+[）)]\s*", "", value)
    value = re.sub(r"^[（(](?:华神|麦种|天道)[）)]\s*", "", value)
    value = re.sub(r"^[◆◇●○■□▲△★☆※·•]+", "", value)
    value = re.sub(r"(?:_|\s+)(?:\d{7,})$", "", value)
    value = re.sub(r"\s*(?:完整版|非完整版|扫描版|掃描版)$", "", value)
    value = re.sub(r"\s+(?:pdf|rar|SD)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"【[^】]*(?:页|P|\d{4}[.年])[^】]*】", "", value, flags=re.IGNORECASE)
    ancient = re.match(r"^(古代基督信仰圣经注释)\s*[（(]\s*(?P<inner>[^）)]+)\s*[）)]$", value)
    if ancient:
        inner = re.sub(r"\s*[-—:：]\s*", "：", ancient.group("inner"))
        inner = inner.replace(":", "：")
        value = f"{ancient.group(1)}：{inner}"
    ancient_space = re.match(r"^(古代基督信仰圣经注释)\s+(?P<inner>.+)$", value)
    if ancient_space:
        inner = re.sub(r"\s*[-—:：]\s*", "：", ancient_space.group("inner"))
        inner = inner.replace(":", "：")
        value = f"{ancient_space.group(1)}：{inner}"
    value = re.sub(r"^[【〖](?P<inner>[^】〗]{2,80})[】〗]$", r"\g<inner>", value)
    value = re.sub(r"^[【〖][^】〗]{2,40}[】〗]\s*(?=.+[\u3400-\u9fffA-Za-z])", "", value)
    value = value.strip("《》〈〉 ")
    value = re.sub(r"^\d{1,3}[：:]\s*", "", value)
    value = re.sub(r"^篇(?=以基督)", "", value)
    value = re.sub(r"[“”‘’]", "", value)
    value = re.sub(r"^\d{2,4}[A-Za-z]{1,6}\d{2,8}\s*", "", value)
    value = re.sub(r"^\d{7,}(?=[\u3400-\u9fff])", "", value)
    value = re.sub(r"^\d{1,3}[A-Za-z](?=研[经經])", "", value)
    value = re.sub(r"^0\d{1,3}(?=[\u3400-\u9fff])", "", value)
    value = re.sub(r"(?<=\d)[：:](?=\d)", "-", value)
    bible_prefix_pattern = "|".join(map(re.escape, BIBLE_TITLE_PREFIX_WORDS))
    value = re.sub(r"^(?:\d{1,4}[、.．]\s*)+", "", value)
    value = re.sub(
        rf"^(?:\d{{1,2}}\s+){{1,3}}\d{{1,2}}(?=(?:{bible_prefix_pattern}))",
        "",
        value,
    )
    value = re.sub(rf"^(?:\d{{1,2}}\s+){{1,3}}(?=(?:{bible_prefix_pattern}))", "", value)
    value = re.sub(
        rf"^\d{{1,2}}(?=(?:{bible_prefix_pattern}|一个|丁道尔|丁道爾))",
        "",
        value,
    )
    value = re.sub(
        rf"^\d{{1,3}}(?:\.\d{{1,3}}[A-Za-z]?)?(?:-\d{{1,2}})?\s*[-—:：]\s*(?={MAIZHONG_COMMENTARY})",
        "",
        value,
    )
    value = re.sub(r"^\d{7,}[：:]\s*", "", value)
    value = re.sub(r"[:：]?fenleiID\s*[A-Za-z0-9]+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[:：]?\s*(?:p|pg)\s*\d+\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^(?:0[1-9]|1[0-3])(?=巴克莱圣经注释)", "", value)
    value = value.replace("_", " ")
    value = strip_catalog_code_prefix(value)
    value = re.sub(r"^篇(?=以基督)", "", value)
    ancient = re.match(r"^(古代基督信仰圣经注释)\s*[（(]\s*(?P<inner>[^）)]+)\s*[）)]$", value)
    if ancient:
        inner = re.sub(r"\s*[-—:：]\s*", "：", ancient.group("inner"))
        inner = inner.replace(":", "：")
        value = f"{ancient.group(1)}：{inner}"
    ancient_space = re.match(r"^(古代基督信仰圣经注释)\s+(?P<inner>.+)$", value)
    if ancient_space:
        inner = re.sub(r"\s*[-—:：]\s*", "：", ancient_space.group("inner"))
        inner = inner.replace(":", "：")
        value = f"{ancient_space.group(1)}：{inner}"
    value = re.sub(r"^\d{7,}\s+", "", value)
    value = re.sub(r"[:：]?\s*fenleiID\s*[A-Za-z0-9]+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[:：]?\s*(?:p|pg)\s*\d+\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*(?:--+|——+)\s*", "：", value)
    value = re.sub(rf"^({TYNDALE_COMMENTARY_PATTERN})\s*[-—:：]\s*", r"\1：", value)
    value = re.sub(rf"^({TYNDALE_COMMENTARY_PATTERN})：\s*\d{{1,2}}\s*[-—:：]\s*", r"\1：", value)
    value = re.sub(rf"^({MAIZHONG_COMMENTARY})\s+", r"\1：", value)
    value = re.sub(rf"^({MAIZHONG_COMMENTARY})(?=[\u3400-\u9fff])", r"\1：", value)
    value = re.sub(r"(?<=[、，,])\s*\d{1,2}\s*[-—:：]\s*", "", value)
    value = re.sub(r"[-—_ ]+[\u3400-\u9fff]{2,20}出版社.*$", "", value)
    value = re.sub(r"[<>|\\/*?\"`~]+", " ", value)
    value = re.sub(r"[:：]\s*(?=[〉》])", "", value)
    value = re.sub(r"(?<=[〉》）\]\)])\s*表格$", "", value)
    value = re.sub(r"(?<=[\u3400-\u9fffA-Za-z0-9]):(?=[\u3400-\u9fff])", "：", value)
    value = re.sub(r"(?<=[\u3400-\u9fff]),(?=[\u3400-\u9fff])", "，", value)
    value = re.sub(r"\s+", " ", value).strip(" ._-：:、，,")
    if value.startswith("古代基督信仰圣经注释："):
        value = value.replace(":", "：")
    if re.fullmatch(r"\d+", value):
        return "书名待核"
    return value or "书名待核"


def sort_title(value: str) -> str:
    title = normalize(value)
    title = re.sub(r"^\d{7,}[：:\s]+", "", title)
    title = re.sub(r"^(?:\d{1,4}[\s、.．：:-]+)+", "", title)
    title = re.sub(r"^\d{1,3}(?=[\u3400-\u9fff])", "", title)
    return title or normalize(value)


def public_row_sort_key(row: dict[str, object]) -> tuple[int, str, str]:
    title = str(row.get("clean_title") or "").strip()
    noisy_prefix = 1 if re.match(r"^[0-9A-Za-z]", title) else 0
    return (noisy_prefix, sort_title(title).casefold(), str(row.get("id") or ""))


def split_title_author(object_key: str) -> tuple[str, str]:
    filename = PurePosixPath(object_key).name
    stem = re.sub(r"\.zip$", "", normalize(filename), flags=re.IGNORECASE)
    stem = re.sub(r"\.(?:pdf|rar|epub|mobi)$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"~?微信[:：]?[A-Za-z0-9_-]+.*$", "", stem, flags=re.IGNORECASE)
    stem = remove_copy_markers(stem)
    stem = re.sub(r"\s*[-_ ]?repaired\s*$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"_(?:\d{7,})$", "", stem)

    tyndale = re.match(
        rf"^({TYNDALE_COMMENTARY_PATTERN})\s*(?:--+|[-_—:：])\s*(?:\d{{1,2}}\s*(?:--+|[-_—:：])\s*)?(?P<title>.+)$",
        stem,
    )
    if tyndale and re.search(r"[\u3400-\u9fff]", tyndale.group("title")):
        return clean_title(f"{tyndale.group(1)}：{tyndale.group('title')}"), ""

    maizhong = re.match(
        rf"^(?:(?:\d{{1,3}}\.)?\d{{1,3}}(?:\.\d{{1,3}}[A-Za-z]?)?(?:-\d{{1,2}})?\s*[-—:：]\s*)?"
        rf"(?P<series>{MAIZHONG_COMMENTARY})\s*"
        rf"(?P<title>.+)$",
        stem,
    )
    if maizhong and re.search(r"[\u3400-\u9fff]", maizhong.group("title")):
        pieces = [
            piece.strip()
            for piece in re.split(r"\s*(?:[：:]|--+|——+|[-—])\s*", maizhong.group("title"))
            if piece.strip()
        ]
        while pieces and (
            pieces[-1] in UNKNOWN_AUTHOR_WORDS
            or clean_person(pieces[-1]) in UNKNOWN_AUTHOR_WORDS
        ):
            pieces.pop()
        author = ""
        if len(pieces) >= 2 and looks_like_person(pieces[-1]):
            author = clean_person(pieces[-1])
            pieces = pieces[:-1]
        title = "".join(pieces) if len(pieces) == 1 else "：".join(pieces)
        return clean_title(f"{maizhong.group('series')}：{title}"), author

    maizhong_parenthetical = re.match(
        r"^(?P<title>.+?)[（(]\s*麦种(?:[.．:：\-—]\s*(?P<author>[^）)]+))?\s*[）)]$",
        stem,
    )
    if maizhong_parenthetical:
        author = maizhong_parenthetical.group("author") or ""
        return clean_title(maizhong_parenthetical.group("title")), clean_person(author)

    maizhong_source = any(
        is_maizhong_source(part)
        for part in re.split(r"\s*(?:--+|——+|[-_—:：])\s*", stem)
        if part.strip()
    ) or re.search(r"[（(]\s*(?:麦种|麦种出版|麦种彩色版|麦种传道会|美国麦种传道会)\s*[）)]", stem)
    if maizhong_source:
        parts = [
            part.strip()
            for part in re.split(r"\s*(?:--+|——+|[-_—:：])\s*", stem)
            if part.strip()
        ]
        removed_code = False
        while parts and (
            re.fullmatch(r"\d{1,3}(?:\.\d{1,3}[A-Za-z]?){0,3}", parts[0])
            or (removed_code and re.fullmatch(r"\d{1,2}", parts[0]))
        ):
            parts.pop(0)
            removed_code = True
        parts = [part for part in parts if not is_maizhong_source(part)]
        author = ""
        if len(parts) >= 2 and looks_like_maizhong_author(parts[-1]):
            author = clean_person(parts[-1])
            parts = parts[:-1]
        title = "：".join(parts) if parts else stem
        return clean_title(title), author

    catalog_code = split_catalog_code_title_author(stem)
    if catalog_code:
        return catalog_code

    bibliographic = re.match(
        r"^[（(](?:中|英|美|德|俄|澳|法)[）)](?P<author>[\u3400-\u9fff·.A-Za-z ]{2,24})著[；;].*?[.。]\s*(?P<title>.+?)(?:[.。]\s*(?:北京|上海|香港).*)?$",
        stem,
    )
    if bibliographic and looks_like_person(bibliographic.group("author")):
        return clean_title(bibliographic.group("title")), clean_person(
            bibliographic.group("author")
        )

    author = ""
    start = stem.find("《")
    end = stem.find("》", start + 1)
    if start >= 0 and end > start:
        prefix, title, suffix = stem[:start], stem[start + 1 : end], stem[end + 1 :]
        second_start = suffix.find("《")
        second_end = suffix.find("》", second_start + 1)
        if second_start >= 0 and second_end > second_start:
            second_title = suffix[second_start + 1 : second_end]
            if re.search(r"[\u3400-\u9fff]", second_title):
                title = second_title
            suffix = suffix[second_end + 1 :]
        if looks_like_person(prefix):
            author = clean_person(prefix)

        volume = re.match(r"^\s*(卷?[上下]|上册|下册)\s*[-—_ ]+\s*(.+)$", suffix)
        if volume:
            title = f"{title} {volume.group(1)}"
            suffix = volume.group(2)

        role = re.search(
            r"(?P<author>[A-Za-z.\s\u3400-\u9fff·、]{2,30}?)(?:著(?!名|作|者)|着|主编|編著|编著)",
            suffix,
        )
        if not author and role and looks_like_person(role.group("author")):
            author = clean_person(role.group("author"))
        elif not author and looks_like_person(suffix):
            author = clean_person(suffix)

        working = re.sub(r"^改革宗经典[-—]+", "", title)
        parts = [part.strip() for part in re.split(r"\s*[-—]\s*", working) if part.strip()]
        numeric_tail = len(parts) >= 2 and all(
            re.fullmatch(r"\d+", part) for part in parts[1:]
        )
        if len(parts) >= 2 and parts[0] == "君王的使者":
            author = parts[0]
            title = "：".join(parts[1:])
        elif not author and len(parts) >= 2 and not numeric_tail and looks_like_person(parts[0]):
            author = clean_person(parts[0])
            title = "：".join(parts[1:])
        elif numeric_tail:
            title = " ".join(parts)
        else:
            title = working
        return clean_title(title), author

    stem = stem.strip("《》")
    role = re.search(
        r"(?P<title>.+?)[_\-—\s]+(?P<author>[A-Za-z.\s\u3400-\u9fff·、]{2,30}?)(?:著(?!名|作|者)|着|主编|編著|编著)(?:\b|[-—_，,;；]|$)",
        stem,
    )
    if role and looks_like_person(role.group("author")):
        return clean_title(role.group("title")), clean_person(role.group("author"))

    parts = [part.strip() for part in re.split(r"\s*(?:--+|——+|[-_])\s*", stem) if part.strip()]
    while parts and (
        clean_person(parts[-1]) in UNKNOWN_AUTHOR_WORDS
        or re.search(r"出版社|出版|小组聚会材料|時間|时间", parts[-1])
    ):
        parts.pop()
    if len(parts) >= 2 and looks_like_person(parts[-1]):
        author = clean_person(parts[-1])
        stem = "：".join(parts[:-1])
    elif len(parts) >= 2 and looks_like_person(parts[0]):
        author = clean_person(parts[0])
        stem = "：".join(parts[1:])
    elif parts:
        stem = "：".join(parts)
    return clean_title(stem), author


def classify(title: str) -> tuple[str, list[str]]:
    normalized = normalize(title).casefold()
    for category, keywords in CATEGORY_RULES:
        matches = [keyword for keyword in keywords if normalize(keyword).casefold() in normalized]
        if matches:
            return category, matches[:3]
    return "other", []


def load_mapping(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_asset_manifest(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None or not path.is_file():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        book_id = str(row.get("id") or "").strip()
        if not book_id:
            continue
        result[book_id] = {key: str(value or "").strip() for key, value in row.items()}
    return result


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def import_inventory(
    inventory_path: Path,
    mapping_path: Path,
    output_path: Path,
    assets_path: Path | None = None,
) -> int:
    objects = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(objects, list):
        raise ValueError("清单必须是对象数组")

    old_mapping = load_mapping(mapping_path)
    assets_by_id = load_asset_manifest(assets_path)
    by_key = {row["object_key"]: row for row in old_mapping if row.get("object_key")}
    by_signature: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in old_mapping:
        if row.get("etag"):
            by_signature[(row.get("size", ""), row["etag"])].append(row)

    used_ids: set[str] = set()
    next_id = max(
        (int(match.group(1)) for row in old_mapping if (match := re.fullmatch(r"cdl-(\d+)", row.get("id", "")))),
        default=0,
    ) + 1
    current_keys = {str(item["key"]) for item in objects}
    mapping_rows: list[dict[str, object]] = []
    public_rows: list[dict[str, object]] = []

    for item in sorted(objects, key=lambda value: normalize(str(value["key"])).casefold()):
        object_key = str(item["key"])
        size = str(item.get("size", ""))
        etag = str(item.get("etag", ""))
        previous = by_key.get(object_key)
        if previous is None and etag:
            candidates = [
                row
                for row in by_signature.get((size, etag), [])
                if row.get("object_key") not in current_keys and row.get("id") not in used_ids
            ]
            previous = candidates[0] if len(candidates) == 1 else None

        if previous and previous.get("id") not in used_ids:
            book_id = previous["id"]
        else:
            book_id = f"cdl-{next_id:06d}"
            next_id += 1
        used_ids.add(book_id)

        title, author = split_title_author(object_key)
        category, tags = classify(title)
        reviewed = previous and previous.get("reviewed", "").lower() == "true"
        if reviewed:
            title = previous.get("clean_title", title) or title
            author = previous.get("author", author)
            category = previous.get("category", category) or category
        assets = assets_by_id.get(book_id, {})
        preview_page_count = assets.get("preview_page_count") or "5"
        if not re.fullmatch(r"\d{1,2}", preview_page_count):
            preview_page_count = "5"

        mapping_rows.append(
            {
                "id": book_id,
                "object_key": object_key,
                "size": size,
                "etag": etag,
                "clean_title": title,
                "author": author,
                "category": category,
                "reviewed": "true" if reviewed else "false",
            }
        )
        public_rows.append(
            {
                "id": book_id,
                "clean_title": title,
                "author": author,
                "publisher": "",
                "year": "",
                "language": "中文",
                "category": category,
                "tags": ";".join(tags),
                "description": "",
                "table_of_contents": "",
                "cover_image_url": assets.get("cover_image_url", ""),
                "preview_page_count": preview_page_count,
                "preview_base_url": assets.get("preview_base_url", ""),
                "access_required": "true",
                "access_url": "",
                "copyright_status": "待核实",
                "can_public_download": "false",
            }
        )

    public_rows.sort(key=public_row_sort_key)
    write_csv(mapping_path, MAPPING_FIELDS, mapping_rows)
    write_csv(output_path, BOOK_FIELDS, public_rows)
    return len(public_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将私有清单转换为公开书目")
    parser.add_argument("--inventory", type=Path, required=True, help="私有对象清单 JSON")
    parser.add_argument("--mapping", type=Path, required=True, help="本机私有编号映射 CSV")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "books.csv")
    parser.add_argument("--assets", type=Path, help="可选：封面和预览图片公开地址清单 CSV")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    try:
        count = import_inventory(args.inventory, args.mapping, args.output, args.assets)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"导入失败：{exc}")
        return 1
    print(f"导入完成：生成 {count} 条公开书目。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
