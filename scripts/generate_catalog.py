#!/usr/bin/env python3
"""从公开书目元数据生成中文静态数字图书馆。"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from string import Template
from typing import Any


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
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class CatalogError(ValueError):
    """书目数据不符合公开目录要求。"""


def escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def book_filter_text(book: dict[str, Any], category: dict[str, str]) -> str:
    return " ".join(
        str(part or "")
        for part in (
            book["clean_title"],
            book["author"],
            book["publisher"],
            book["year"],
            book["language"],
            category["name"],
            book["description"],
            " ".join(book["tags"]),
        )
        if part
    )


def load_categories(path: Path) -> list[dict[str, str]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"无法读取分类数据：{exc}") from exc

    if not isinstance(raw, list) or not raw:
        raise CatalogError("categories.json 必须是非空数组")

    categories: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise CatalogError(f"第 {index} 个分类必须是对象")
        category_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        description = str(item.get("description", "")).strip()
        if not ID_PATTERN.fullmatch(category_id):
            raise CatalogError(f"分类 id 不合法：{category_id!r}")
        if not name:
            raise CatalogError(f"分类 {category_id} 缺少中文名称")
        if category_id in seen:
            raise CatalogError(f"分类 id 重复：{category_id}")
        seen.add(category_id)
        categories.append({"id": category_id, "name": name, "description": description})
    return categories


def load_books(path: Path, valid_categories: set[str]) -> list[dict[str, Any]]:
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise CatalogError(f"无法读取图书数据：{exc}") from exc

    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != BOOK_FIELDS:
            raise CatalogError(
                "books.csv 字段必须严格按照规范排列。\n"
                f"期望：{', '.join(BOOK_FIELDS)}\n"
                f"实际：{', '.join(reader.fieldnames or [])}"
            )

        books: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            book = {key: (value or "").strip() for key, value in row.items()}
            book_id = book["id"]
            if not ID_PATTERN.fullmatch(book_id):
                raise CatalogError(f"第 {line_number} 行 id 不合法：{book_id!r}")
            if book_id in seen:
                raise CatalogError(f"第 {line_number} 行 id 重复：{book_id}")
            if not book["clean_title"]:
                raise CatalogError(f"第 {line_number} 行缺少 clean_title")
            if book["category"] not in valid_categories:
                raise CatalogError(
                    f"第 {line_number} 行引用了未定义分类：{book['category']!r}"
                )
            if not book["copyright_status"]:
                raise CatalogError(f"第 {line_number} 行缺少 copyright_status")
            if book["can_public_download"].lower() not in {"true", "false"}:
                raise CatalogError(
                    f"第 {line_number} 行 can_public_download 只能是 true 或 false"
                )
            if book["access_required"].lower() not in {"true", "false"}:
                raise CatalogError(
                    f"第 {line_number} 行 access_required 只能是 true 或 false"
                )
            if book["preview_page_count"]:
                if not re.fullmatch(r"\d{1,2}", book["preview_page_count"]):
                    raise CatalogError(
                        f"第 {line_number} 行 preview_page_count 应为 0 到 20 的数字"
                    )
                preview_page_count = int(book["preview_page_count"])
                if preview_page_count > 20:
                    raise CatalogError(
                        f"第 {line_number} 行 preview_page_count 不应超过 20"
                    )
            else:
                preview_page_count = 0
            if book["year"] and not re.fullmatch(r"\d{4}", book["year"]):
                raise CatalogError(f"第 {line_number} 行 year 应为四位年份或留空")

            seen.add(book_id)
            book["can_public_download"] = book["can_public_download"].lower() == "true"
            book["access_required"] = book["access_required"].lower() == "true"
            book["preview_page_count"] = preview_page_count
            book["tags"] = [
                part.strip()
                for part in re.split(r"[;；]", book["tags"])
                if part.strip()
            ]
            book["table_of_contents"] = [
                part.strip() for part in book["table_of_contents"].split("|") if part.strip()
            ]
            books.append(book)
    return books


def render_layout(
    template: Template,
    *,
    title: str,
    description: str,
    content: str,
    active: str,
    root_prefix: str = ".",
) -> str:
    nav = {
        name: ' aria-current="page"' if name == active else ""
        for name in ("home", "catalog", "categories", "about")
    }
    return template.substitute(
        page_title=escape(title),
        page_description=escape(description),
        content=content,
        root_prefix=root_prefix,
        nav_home=nav["home"],
        nav_catalog=nav["catalog"],
        nav_categories=nav["categories"],
        nav_about=nav["about"],
    )


def render_book_card(
    book: dict[str, Any], categories: dict[str, dict[str, str]], link_prefix: str = ""
) -> str:
    author = book["author"] or "作者待核"
    byline = " · ".join(part for part in (author, book["year"]) if part)
    description = (
        f'<p class="description">{escape(book["description"])}</p>'
        if book["description"]
        else ""
    )
    category = categories[book["category"]]
    filter_text = book_filter_text(book, category)
    return f"""
        <article class="card" data-filter-text="{escape(filter_text)}">
          <h3><a href="{link_prefix}books/{escape(book['id'])}.html">{escape(book['clean_title'])}</a></h3>
          <p class="meta">{escape(byline)}</p>
          {description}
          <div class="card-footer">
            <span class="badge">{escape(category['name'])}</span>
            <span class="meta">查看书目 →</span>
          </div>
        </article>"""


def good_homepage_feature(book: dict[str, Any]) -> bool:
    title = str(book.get("clean_title") or "").strip()
    if not title:
        return False
    if re.match(r"^[0-9A-Za-z]", title):
        return False
    if title.isdigit():
        return False
    return True


def sort_title(value: str) -> str:
    title = str(value or "").strip()
    title = re.sub(r"^\d{7,}[：:\s]+", "", title)
    title = re.sub(r"^(?:\d{1,4}[\s、.．：:-]+)+", "", title)
    title = re.sub(r"^\d{1,3}(?=[\u3400-\u9fff])", "", title)
    return title or str(value or "").strip()


def book_sort_key(book: dict[str, Any]) -> tuple[int, str, str]:
    title = str(book.get("clean_title") or "").strip()
    noisy_prefix = 1 if re.match(r"^[0-9A-Za-z]", title) else 0
    return (noisy_prefix, sort_title(title).casefold(), str(book.get("id") or ""))


def render_home(
    template: Template,
    books: list[dict[str, Any]],
    categories: list[dict[str, str]],
    category_map: dict[str, dict[str, str]],
) -> str:
    counts = Counter(book["category"] for book in books)
    featured_books = [book for book in books if good_homepage_feature(book)][:6] or books[:6]
    featured = "".join(render_book_card(book, category_map) for book in featured_books)
    category_cards = "".join(
        f"""
        <article class="card">
          <h3><a href="categories/{escape(category['id'])}.html">{escape(category['name'])}</a></h3>
          <p class="description">{escape(category['description'])}</p>
          <div class="card-footer">
            <span class="badge">{counts[category['id']]} 条书目</span>
            <span class="meta">浏览分类 →</span>
          </div>
        </article>"""
        for category in categories
        if counts[category["id"]]
    )
    if not featured:
        featured = '<div class="empty-state">书目正在整理中。</div>'
    if not category_cards:
        category_cards = '<div class="empty-state">分类内容正在整理中。</div>'
    content = f"""
    <section class="hero">
      <div class="shell hero-grid">
        <div>
          <p class="eyebrow">中文基督教数字图书馆</p>
          <h1>在浩繁馆藏中，找到想读的那一本。</h1>
          <p class="lead">按书名、作者和主题检索中文基督教书目，快速浏览馆藏内容。</p>
          <div class="actions">
            <a class="button" href="catalog.html">搜索馆藏</a>
            <a class="button secondary" href="categories.html">按分类浏览</a>
          </div>
          <div class="stats" aria-label="馆藏统计">
            <div class="stat"><strong>{len(books)}</strong><span>条馆藏书目</span></div>
            <div class="stat"><strong>{sum(1 for count in counts.values() if count)}</strong><span>个已有内容的分类</span></div>
          </div>
        </div>
        <aside class="hero-note">
          <strong>目录持续整理</strong>
          <p>书名、作者、版本与分类会在核对后逐步补充和修正。</p>
        </aside>
      </div>
    </section>
    <section class="section tint">
      <div class="shell">
        <div class="section-heading">
          <div><p class="eyebrow">开始探索</p><h2>按主题走进馆藏</h2></div>
          <a href="categories.html">查看全部分类</a>
        </div>
        <div class="grid">{category_cards}</div>
      </div>
    </section>
    <section class="section">
      <div class="shell">
        <div class="section-heading">
          <div><p class="eyebrow">馆藏目录</p><h2>最近整理的书目</h2></div>
          <a href="catalog.html">进入完整目录</a>
        </div>
        <div class="grid">{featured}</div>
      </div>
    </section>"""
    return render_layout(
        template,
        title="基督教数字图书馆｜中文馆藏平台",
        description="面向中文读者的基督教数字图书馆，提供审慎整理的书目搜索与分类浏览。",
        content=content,
        active="home",
    )


def render_catalog(template: Template, categories: list[dict[str, str]]) -> str:
    options = "".join(
        f'<option value="{escape(category["id"])}">{escape(category["name"])}</option>'
        for category in categories
    )
    content = f"""
    <header class="page-hero">
      <div class="shell">
        <p class="eyebrow">书目搜索</p>
        <h1>搜索书目</h1>
        <p class="lead">可按书名、作者、标签和分类检索。</p>
      </div>
    </header>
    <section class="section">
      <div class="shell">
        <div class="search-panel" role="search">
          <div class="field">
            <label for="search-input">关键词</label>
            <input id="search-input" type="search" placeholder="例如：马丁·路德、诗篇、家庭" autocomplete="off">
          </div>
          <div class="field">
            <label for="category-filter">分类</label>
            <select id="category-filter">
              <option value="">全部分类</option>
              {options}
            </select>
          </div>
        </div>
        <p id="result-summary" class="result-summary" aria-live="polite">正在读取书目……</p>
        <div id="search-results" class="grid"></div>
        <div class="load-more-wrap"><button id="load-more" class="button secondary" type="button" hidden>显示更多</button></div>
        <noscript><div class="empty-state">搜索功能需要 JavaScript。你仍可前往“分类”页面浏览全部书目。</div></noscript>
      </div>
    </section>
    <script src="assets/search.js" defer></script>"""
    return render_layout(
        template,
        title="书目目录｜基督教数字图书馆",
        description="搜索基督教数字图书馆的中文书目元数据。",
        content=content,
        active="catalog",
    )


def render_categories(
    template: Template,
    books: list[dict[str, Any]],
    categories: list[dict[str, str]],
) -> str:
    counts = Counter(book["category"] for book in books)
    cards = "".join(
        f"""
        <article class="card">
          <h3><a href="categories/{escape(category['id'])}.html">{escape(category['name'])}</a></h3>
          <p class="description">{escape(category['description'])}</p>
          <div class="card-footer"><span class="badge">{counts[category['id']]} 条书目</span><span class="meta">进入分类 →</span></div>
        </article>"""
        for category in categories
    )
    content = f"""
    <header class="page-hero"><div class="shell">
      <p class="eyebrow">按主题浏览</p><h1>馆藏分类</h1>
      <p class="lead">分类用于稳定组织书目；标签则补充人物、主题与用途等交叉线索。</p>
    </div></header>
    <section class="section"><div class="shell"><div class="grid">{cards}</div></div></section>"""
    return render_layout(
        template,
        title="馆藏分类｜基督教数字图书馆",
        description="按主题浏览基督教数字图书馆的中文书目。",
        content=content,
        active="categories",
    )


def render_category_detail(
    template: Template,
    category: dict[str, str],
    books: list[dict[str, Any]],
    category_map: dict[str, dict[str, str]],
) -> str:
    cards = "".join(
        render_book_card(book, category_map, link_prefix="../") for book in books
    )
    if not cards:
        cards = '<div class="empty-state">这个分类暂时没有已整理的书目。</div>'
    content = f"""
    <header class="page-hero"><div class="shell">
      <nav class="breadcrumbs" aria-label="面包屑"><a href="../categories.html">馆藏分类</a> / {escape(category['name'])}</nav>
      <p class="eyebrow">馆藏分类</p><h1>{escape(category['name'])}</h1>
      <p class="lead">{escape(category['description'])}</p>
    </div></header>
    <section class="section"><div class="shell">
      <div class="search-panel category-filter-panel" role="search">
        <div class="field">
          <label for="category-search-input">在本分类中筛选</label>
          <input id="category-search-input" type="search" placeholder="输入书名、作者、标签或关键词" autocomplete="off">
        </div>
      </div>
      <p id="category-result-summary" class="result-summary" aria-live="polite">共 {len(books)} 条书目</p>
      <div id="category-results" class="grid" data-category-total="{len(books)}">{cards}</div>
      <div id="category-empty-state" class="empty-state" hidden>没有找到匹配的书目，请尝试缩短关键词。</div>
    </div></section>
    <script src="../assets/category-filter.js" defer></script>"""
    return render_layout(
        template,
        title=f"{category['name']}｜基督教数字图书馆",
        description=category["description"],
        content=content,
        active="categories",
        root_prefix="..",
    )


def render_preview_section(book: dict[str, Any]) -> str:
    page_count = int(book.get("preview_page_count") or 0)
    base_url = str(book.get("preview_base_url") or "").strip().rstrip("/")

    if page_count <= 0:
        return """
        <section class="book-section">
          <h2>预览</h2>
          <div class="empty-state">预览页正在整理中。</div>
        </section>"""

    if base_url:
        pages = "".join(
            f"""
            <figure class="preview-page">
              <button class="media-viewer-trigger preview-page-button" type="button" data-media-viewer-item data-media-group="preview" data-media-src="{escape(base_url)}/page-{index}.jpg" data-media-caption="{escape(book['clean_title'])} · 第 {index} 页">
                <img src="{escape(base_url)}/page-{index}.jpg" alt="{escape(book['clean_title'])} 第 {index} 页预览" loading="lazy">
              </button>
              <figcaption>第 {index} 页</figcaption>
            </figure>"""
            for index in range(1, page_count + 1)
        )
    else:
        pages = "".join(
            f"""
            <div class="preview-page preview-placeholder">
              <span>第 {index} 页</span>
              <small>预览图待生成</small>
            </div>"""
            for index in range(1, page_count + 1)
        )

    preview_title = f"前 {page_count} 页预览" if page_count > 1 else "第 1 页预览"
    return f"""
        <section class="book-section">
          <div class="section-heading compact">
            <div><h2>{escape(preview_title)}</h2></div>
            <span class="badge">公开预览</span>
          </div>
          <div class="preview-grid">{pages}</div>
        </section>"""


def cover_image_url(book: dict[str, Any]) -> str:
    explicit_cover = str(book.get("cover_image_url") or "").strip()
    if explicit_cover:
        return explicit_cover
    base_url = str(book.get("preview_base_url") or "").strip().rstrip("/")
    if base_url:
        return f"{base_url}/page-1.jpg"
    return ""


def render_cover_section(book: dict[str, Any]) -> str:
    cover_url = cover_image_url(book)
    if cover_url:
        cover = f"""
          <button class="media-viewer-trigger book-cover-button" type="button" data-media-viewer-item data-media-group="cover" data-media-src="{escape(cover_url)}" data-media-caption="{escape(book['clean_title'])} · 封面">
            <img src="{escape(cover_url)}" alt="{escape(book['clean_title'])} 封面" loading="lazy">
          </button>"""
    else:
        cover = f"""
          <div class="book-cover-placeholder">
            <span>{escape(book['clean_title'])}</span>
            <small>封面待生成</small>
          </div>"""

    return f"""
        <section class="book-cover-card" aria-label="书籍封面">
          {cover}
        </section>"""


def render_access_section(book: dict[str, Any]) -> str:
    if not book.get("access_required"):
        return """
        <section class="access-panel">
          <h2>全文访问</h2>
          <p>此书目当前不需要访问密码。</p>
        </section>"""

    return f"""
        <section class="access-panel">
          <h2>下载或阅读全文</h2>
          <p>下载文件或查看完整内容需要访问密码。</p>
          <form class="access-form" data-access-form>
            <input type="hidden" name="book_id" value="{escape(book['id'])}">
            <label for="access-password-{escape(book['id'])}">访问码</label>
            <div class="access-form-row">
              <input id="access-password-{escape(book['id'])}" name="access_code" type="password" autocomplete="current-password" required>
              <button class="button" type="submit" name="access_action" value="read">在线阅读</button>
              <button class="button secondary" type="submit" name="access_action" value="download">下载文件</button>
            </div>
            <p class="meta" data-access-status>访问入口正在接入中。</p>
          </form>
          <p class="meta">访问码由服务端验证，网页不保存访问码。</p>
        </section>"""


def render_book_detail(
    template: Template,
    book: dict[str, Any],
    category: dict[str, str],
) -> str:
    metadata_items = [
        ("作者", book["author"] or "待核实"),
        ("出版社", book["publisher"] or "待核实"),
        ("年份", book["year"] or "待核实"),
        ("语言", book["language"] or "待核实"),
        ("分类", category["name"]),
        ("版权状态", book["copyright_status"]),
    ]
    metadata = "".join(
        f'<div class="metadata-row"><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>'
        for label, value in metadata_items
    )
    tags = "".join(f'<span class="tag">{escape(tag)}</span>' for tag in book["tags"])
    toc = "".join(f"<li>{escape(item)}</li>" for item in book["table_of_contents"])
    toc_section = (
        f'<section class="book-section"><h2>目录</h2><ol class="toc">{toc}</ol></section>'
        if toc
        else '<section class="book-section"><h2>目录</h2><p class="meta">目录信息尚待整理。</p></section>'
    )
    availability = "当前书目用于馆藏查询，文件访问按实际授权情况提供。"
    content = f"""
    <header class="page-hero book-detail-hero"><div class="shell book-hero-grid">
      <div class="book-hero-copy">
        <nav class="breadcrumbs" aria-label="面包屑"><a href="../categories.html">馆藏分类</a> / <a href="../categories/{escape(category['id'])}.html">{escape(category['name'])}</a> / 当前书目</nav>
        <p class="eyebrow">书目编号 · {escape(book['id'])}</p>
        <h1>{escape(book['clean_title'])}</h1>
        <p class="lead">{escape(book['author'] or '作者信息待核实')}</p>
      </div>
      <div class="book-hero-cover">
        {render_cover_section(book)}
      </div>
    </div></header>
    <section class="section"><div class="shell book-layout">
      <div class="book-main">
        <section class="book-section"><h2>内容简介</h2><p>{escape(book['description'] or '暂无内容简介。')}</p></section>
        {render_preview_section(book)}
        {toc_section}
        <section class="book-section"><h2>主题标签</h2><div class="tags">{tags or '<span class="meta">暂无标签</span>'}</div></section>
      </div>
      <aside class="book-aside">
        <section class="book-section"><h2>书目信息</h2><dl class="metadata-list">{metadata}</dl></section>
        {render_access_section(book)}
        <div class="notice"><strong>访问说明</strong><p>{escape(availability)}</p></div>
      </aside>
    </div></section>
    <script src="../assets/access-config.js" defer></script>
    <script src="../assets/access.js" defer></script>
    <script src="../assets/image-viewer.js" defer></script>"""
    return render_layout(
        template,
        title=f"{book['clean_title']}｜基督教数字图书馆",
        description=book["description"] or f"《{book['clean_title']}》书目详情。",
        content=content,
        active="",
        root_prefix="..",
    )


def render_about(template: Template) -> str:
    content = """
    <header class="page-hero"><div class="shell">
      <p class="eyebrow">关于图书馆</p><h1>关于基督教数字图书馆</h1>
      <p class="lead">整理中文基督教馆藏，让查找、浏览和使用资料更简单。</p>
    </div></header>
    <section class="section"><div class="shell prose">
      <h2>馆藏整理</h2>
      <p>网站以书目为基础，持续核对书名、作者、版本、分类和目录。</p>
      <h2>使用范围</h2>
      <p>馆藏资料按实际授权情况提供访问，网站目录会随着整理进度持续更新。</p>
    </div></section>"""
    content += """
    <section class="section tint"><div class="shell">
      <div class="upload-panel">
        <div>
          <p class="eyebrow">上传申请</p>
          <h2>提交书籍资料</h2>
          <p class="description">你可以提交书名、作者和文件。提交后会进入待审核区，不会自动公开显示，也不会自动开放下载。</p>
        </div>
        <form id="upload-request-form" class="upload-form" enctype="multipart/form-data" data-upload-endpoint="">
          <div class="field">
            <label for="upload-title">书名</label>
            <input id="upload-title" name="title" type="text" autocomplete="off" required>
          </div>
          <div class="field">
            <label for="upload-author">作者</label>
            <input id="upload-author" name="author" type="text" autocomplete="off" required>
          </div>
          <div class="field">
            <label for="upload-file">文件</label>
            <input id="upload-file" name="file" type="file" accept=".zip,.pdf,.epub,.mobi" required>
          </div>
          <div class="field">
            <label for="upload-code">提交码</label>
            <input id="upload-code" name="upload_code" type="password" autocomplete="off" required>
            <p class="field-hint">提交码由管理员提供，不会写入公开网页。</p>
          </div>
          <button class="button" type="submit">提交审核</button>
          <p id="upload-request-status" class="form-status" aria-live="polite">上传入口正在接入中。</p>
        </form>
      </div>
    </div></section>
    <script src="assets/upload-config.js" defer></script>
    <script src="assets/upload.js" defer></script>"""
    return render_layout(
        template,
        title="关于项目｜基督教数字图书馆",
        description="了解基督教数字图书馆的目标、存储原则与内容治理方式。",
        content=content,
        active="about",
    )


def public_catalog(
    books: list[dict[str, Any]], category_map: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """只返回可以进入公开静态站点的字段。"""
    result = []
    for book in books:
        item = {key: book[key] for key in BOOK_FIELDS}
        item["category_name"] = category_map[book["category"]]["name"]
        item["detail_url"] = f"books/{book['id']}.html"
        result.append(item)
    return result


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def build_site(root: Path = ROOT, output: Path | None = None) -> dict[str, int]:
    output = output or root / "site"
    root = root.resolve()
    output = output.resolve()
    if output == root or root in output.parents and output.name in {"data", "src", "public"}:
        raise CatalogError(f"拒绝覆盖源目录：{output}")

    categories = load_categories(root / "data" / "categories.json")
    category_map = {category["id"]: category for category in categories}
    books = sorted(load_books(root / "data" / "books.csv", set(category_map)), key=book_sort_key)
    template = Template((root / "src" / "templates" / "base.html").read_text(encoding="utf-8"))

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(root / "public", output)

    write_text(output / "index.html", render_home(template, books, categories, category_map))
    write_text(output / "catalog.html", render_catalog(template, categories))
    write_text(output / "categories.html", render_categories(template, books, categories))
    write_text(output / "about.html", render_about(template))

    for category in categories:
        category_books = [book for book in books if book["category"] == category["id"]]
        write_text(
            output / "categories" / f"{category['id']}.html",
            render_category_detail(template, category, category_books, category_map),
        )
    for book in books:
        write_text(
            output / "books" / f"{book['id']}.html",
            render_book_detail(template, book, category_map[book["category"]]),
        )

    write_text(
        output / "catalog.json",
        json.dumps(public_catalog(books, category_map), ensure_ascii=False, indent=2),
    )
    write_text(output / ".nojekyll", "")
    return {"books": len(books), "categories": len(categories)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成基督教数字图书馆静态网站")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "site",
        help="网站输出目录（默认：site）",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    try:
        counts = build_site(ROOT, args.output)
    except CatalogError as exc:
        print(f"生成失败：{exc}")
        return 1
    print(
        f"生成完成：{counts['books']} 条书目、{counts['categories']} 个分类，"
        f"输出到 {args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
