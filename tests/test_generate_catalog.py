from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_catalog", ROOT / "scripts" / "generate_catalog.py"
)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append(value)


def create_sample_project(parent: Path) -> Path:
    project = parent / "project"
    shutil.copytree(ROOT / "data", project / "data")
    shutil.copytree(ROOT / "public", project / "public")
    shutil.copytree(ROOT / "src", project / "src")
    sample = {
        "id": "sample-book",
        "clean_title": "示例书目",
        "author": "示例作者",
        "publisher": "",
        "year": "2024",
        "language": "中文",
        "category": "theology",
        "tags": "示例;测试",
        "description": "用于自动化测试的虚构书目。",
        "table_of_contents": "第一章|第二章",
        "cover_image_url": "",
        "preview_page_count": "5",
        "preview_base_url": "",
        "access_required": "true",
        "access_url": "",
        "copyright_status": "公共领域",
        "can_public_download": "false",
    }
    with (project / "data" / "books.csv").open(
        "w", encoding="utf-8", newline=""
    ) as target:
        writer = csv.DictWriter(target, fieldnames=GENERATOR.BOOK_FIELDS)
        writer.writeheader()
        writer.writerow(sample)
    return project


class CatalogGenerationTests(unittest.TestCase):
    def test_empty_catalog_generates_core_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            with (project / "data" / "books.csv").open(
                "w", encoding="utf-8", newline=""
            ) as target:
                writer = csv.DictWriter(target, fieldnames=GENERATOR.BOOK_FIELDS)
                writer.writeheader()
            output = project / "site"
            counts = GENERATOR.build_site(project, output)

            self.assertEqual(0, counts["books"])
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "catalog.html").is_file())
            self.assertTrue((output / "categories.html").is_file())
            self.assertTrue((output / "about.html").is_file())
            self.assertEqual(
                [], json.loads((output / "catalog.json").read_text(encoding="utf-8"))
            )

    def test_sample_book_generates_public_catalog_and_detail_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            output = project / "site"
            counts = GENERATOR.build_site(project, output)
            catalog = json.loads((output / "catalog.json").read_text(encoding="utf-8"))

            self.assertEqual(1, counts["books"])
            self.assertTrue((output / "books" / "sample-book.html").is_file())
            self.assertEqual(1, len(catalog))
            self.assertEqual(
                set(GENERATOR.BOOK_FIELDS) | {"category_name", "detail_url"},
                set(catalog[0]),
            )
            detail = (output / "books" / "sample-book.html").read_text(
                encoding="utf-8"
            )
            self.assertIn("前 5 页预览", detail)
            self.assertIn("book-hero-grid", detail)
            self.assertIn("book-hero-cover", detail)
            self.assertIn("book-cover-card", detail)
            self.assertLess(detail.index("book-hero-cover"), detail.index("book-layout"))
            self.assertIn("封面待生成", detail)
            self.assertIn("下载或阅读全文", detail)
            self.assertIn("需要密码", detail)

    def test_preview_heading_uses_actual_page_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            csv_path = project / "data" / "books.csv"
            with csv_path.open(encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            rows[0]["preview_page_count"] = "1"
            rows[0]["preview_base_url"] = "https://example.test/previews/sample-book"
            with csv_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=GENERATOR.BOOK_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

            output = project / "site"
            GENERATOR.build_site(project, output)
            detail = (output / "books" / "sample-book.html").read_text(
                encoding="utf-8"
            )

            self.assertIn("第 1 页预览", detail)
            self.assertNotIn("前 1 页预览", detail)

    def test_about_page_contains_upload_request_form(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            output = project / "site"
            GENERATOR.build_site(project, output)
            about = (output / "about.html").read_text(encoding="utf-8")

            self.assertIn("提交书籍资料", about)
            self.assertIn('name="title"', about)
            self.assertIn('name="author"', about)
            self.assertIn('name="file"', about)
            self.assertIn('name="upload_code"', about)
            self.assertIn('id="upload-code"', about)
            self.assertIn("提交码由管理员提供", about)
            self.assertIn("上传入口正在接入中", about)
            self.assertIn("assets/upload.js", about)

    def test_category_detail_page_contains_filter_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            output = project / "site"
            GENERATOR.build_site(project, output)
            category = (output / "categories" / "theology.html").read_text(
                encoding="utf-8"
            )

            self.assertIn('id="category-search-input"', category)
            self.assertIn('id="category-result-summary"', category)
            self.assertIn('id="category-results"', category)
            self.assertIn('id="category-empty-state"', category)
            self.assertIn('data-filter-text=', category)
            self.assertIn('../assets/category-filter.js', category)

    def test_generated_site_has_no_download_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            output = project / "site"
            GENERATOR.build_site(project, output)
            combined = "\n".join(
                path.read_text(encoding="utf-8")
                for path in output.rglob("*")
                if path.is_file() and path.suffix in {".html", ".json"}
            )

            self.assertNotRegex(combined, r"href=[\"'][^\"']+\.(?:zip|pdf|epub)")

    def test_hidden_controls_are_not_forced_visible_by_button_styles(self) -> None:
        css = (ROOT / "public" / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("[hidden]", css)
        self.assertIn("display: none", css)

    def test_header_does_not_overlay_page_content(self) -> None:
        css = (ROOT / "public" / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertNotIn("position: sticky", css)

    def test_homepage_feature_prefers_clean_titles(self) -> None:
        self.assertFalse(GENERATOR.good_homepage_feature({"clean_title": "003cc0701 合神心意的敬拜"}))
        self.assertFalse(GENERATOR.good_homepage_feature({"clean_title": "10丁道尔"}))
        self.assertTrue(GENERATOR.good_homepage_feature({"clean_title": "个人的属灵生活"}))

    def test_book_sort_key_pushes_numbered_titles_back(self) -> None:
        books = [
            {"id": "b", "clean_title": "100名画旧约"},
            {"id": "a", "clean_title": "个人的属灵生活"},
            {"id": "c", "clean_title": "09 10圣经信息系列 撒母耳记上下"},
        ]
        titles = [book["clean_title"] for book in sorted(books, key=GENERATOR.book_sort_key)]
        self.assertEqual("个人的属灵生活", titles[0])
        self.assertCountEqual(["100名画旧约", "09 10圣经信息系列 撒母耳记上下"], titles[1:])

    def test_generated_links_work_under_github_project_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            output = project / "site"
            GENERATOR.build_site(project, output)
            root_page = (output / "index.html").read_text(encoding="utf-8")
            detail_page = (output / "books" / "sample-book.html").read_text(
                encoding="utf-8"
            )

            self.assertIn('href="./assets/styles.css"', root_page)
            self.assertIn('href="../assets/styles.css"', detail_page)
            self.assertNotRegex(root_page + detail_page, r'(?:href|src)=["\']/')
            self.assertNotIn("..//", detail_page)

    def test_all_internal_links_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            output = project / "site"
            GENERATOR.build_site(project, output)
            missing: list[str] = []
            for page in output.rglob("*.html"):
                parser = LinkCollector()
                parser.feed(page.read_text(encoding="utf-8"))
                for link in parser.links:
                    parsed = urlsplit(link)
                    if parsed.scheme or parsed.netloc or not parsed.path:
                        continue
                    target = (page.parent / unquote(parsed.path)).resolve()
                    if not target.exists():
                        missing.append(f"{page.relative_to(output)} -> {link}")
            self.assertEqual([], missing)

    def test_invalid_category_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = create_sample_project(Path(directory))
            csv_path = project / "data" / "books.csv"
            with csv_path.open("r", encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["category"] = "not-a-category"
            with csv_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=GENERATOR.BOOK_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

            with self.assertRaises(GENERATOR.CatalogError):
                GENERATOR.load_books(csv_path, {"theology"})


if __name__ == "__main__":
    unittest.main()
