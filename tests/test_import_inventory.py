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
        self.assertEqual("示例圣经注释-示例书卷", title)
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

    def test_internal_catalog_code_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/003cc0701 合神心意的敬拜.zip")
        self.assertEqual("合神心意的敬拜", title)
        self.assertEqual("", author)

    def test_short_zero_prefixed_series_number_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/02出埃及记卷上--赖建国--天道注释.zip")
        self.assertEqual("出埃及记卷上：赖建国：天道注释", title)
        self.assertEqual("", author)

    def test_multi_number_bible_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/09 10圣经信息系列 撒母耳记上下.zip")
        self.assertEqual("圣经信息系列 撒母耳记上下", title)
        self.assertEqual("", author)

    def test_long_catalog_number_and_page_marker_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/10156162_新约的传说_p258.zip")
        self.assertEqual("新约的传说", title)
        self.assertEqual("", author)

    def test_leading_decorative_marker_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/◆约翰福音注释 马太亨利.zip")
        self.assertEqual("约翰福音注释 马太亨利", title)
        self.assertEqual("", author)

    def test_leading_collection_label_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/【圣经注释】解经讲道注释丛书01：創世记.zip")
        self.assertEqual("解经讲道注释丛书01：創世记", title)
        self.assertEqual("", author)

    def test_repaired_suffix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/【剑桥文学指南】圣经诠释-repaired.zip")
        self.assertEqual("圣经诠释", title)
        self.assertEqual("", author)

    def test_real_title_number_is_kept(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/21世纪基督教灵修学导论.zip")
        self.assertEqual("21世纪基督教灵修学导论", title)
        self.assertEqual("", author)

    def test_trailing_form_noise_after_book_title_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/一步一步学〈诗篇:〉表格.zip")
        self.assertEqual("一步一步学〈诗篇〉", title)
        self.assertEqual("", author)

    def test_tyndale_new_testament_volume_number_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/丁道尔新约注释--01-马太福音.zip")
        self.assertEqual("丁道尔新约注释：马太福音", title)
        self.assertEqual("", author)

    def test_tyndale_embedded_volume_number_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/丁道尔新约注释--13-歌罗西书、16-腓利门书.zip"
        )
        self.assertEqual("丁道尔新约注释：歌罗西书、腓利门书", title)
        self.assertEqual("", author)

    def test_tyndale_revelation_is_not_mistaken_for_author(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/丁道尔新约注释--22-启示录.zip")
        self.assertEqual("丁道尔新约注释：启示录", title)
        self.assertEqual("", author)

    def test_tyndale_hyphen_separator_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/《丁道尔新约圣经注释-雅各书》.zip")
        self.assertEqual("丁道尔新约圣经注释：雅各书", title)
        self.assertEqual("", author)

    def test_tyndale_old_testament_volume_number_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/丁道尔旧约注释--01-创世记.zip")
        self.assertEqual("丁道尔旧约注释：创世记", title)
        self.assertEqual("", author)

    def test_tyndale_old_testament_embedded_volume_number_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/丁道尔旧约注释--08-士师记、路得记.zip")
        self.assertEqual("丁道尔旧约注释：士师记、路得记", title)
        self.assertEqual("", author)

    def test_maizhong_commentary_code_and_publisher_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/94.09：麦种圣经注释 约翰书信：亚伯勒：麦种.zip"
        )
        self.assertEqual("麦种圣经注释：约翰书信", title)
        self.assertEqual("亚伯勒", author)

    def test_maizhong_commentary_code_is_removed_when_author_is_separate(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/224.1.16-1-麦种圣经注释以赛亚书一至三十九章-欧思沃.zip"
        )
        self.assertEqual("麦种圣经注释：以赛亚书一至三十九章", title)
        self.assertEqual("欧思沃", author)

    def test_maizhong_commentary_letter_code_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/227.1.19a-麦种圣经注释罗马书 上 -穆尔-麦种.zip"
        )
        self.assertEqual("麦种圣经注释：罗马书 上", title)
        self.assertEqual("穆尔", author)

    def test_maizhong_catalog_code_and_source_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/227.8.10a-提摩太与提多书信注释上-唐书礼-麦种.zip"
        )
        self.assertEqual("提摩太与提多书信注释上", title)
        self.assertEqual("唐书礼", author)

    def test_maizhong_source_before_author_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/242.2.24-更新的时刻 圣经灵修360-美国麦种传道会-华伦 魏斯比.zip"
        )
        self.assertEqual("更新的时刻 圣经灵修360", title)
        self.assertEqual("华伦 魏斯比", author)

    def test_maizhong_multiple_authors_are_moved_to_author_field(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/225.6.20-1-新约引用旧约上-毕尔、卡森-麦种.zip"
        )
        self.assertEqual("新约引用旧约上", title)
        self.assertEqual("毕尔 卡森", author)

    def test_maizhong_parenthetical_source_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/保罗神学新旧观(麦种).zip")
        self.assertEqual("保罗神学新旧观", title)
        self.assertEqual("", author)

    def test_maizhong_parenthetical_source_with_author_is_split(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/新约神学(麦种.马歇尔).zip")
        self.assertEqual("新约神学", title)
        self.assertEqual("马歇尔", author)

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

    def test_asset_manifest_populates_public_preview_urls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "inventory.json"
            mapping = root / "mapping.csv"
            assets = root / "assets.csv"
            output = root / "books.csv"
            inventory.write_text(
                json.dumps(
                    [{"key": "incoming/示例书卷.zip", "size": 10, "etag": "sample"}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            mapping.write_text(
                "id,object_key,size,etag,clean_title,author,category,reviewed\n"
                "cdl-0001,incoming/示例书卷.zip,10,sample,示例书卷,,bible-study,true\n",
                encoding="utf-8",
            )
            assets.write_text(
                "id,cover_image_url,preview_base_url,preview_page_count\n"
                "cdl-0001,https://example.test/covers/cdl-0001.jpg,https://example.test/previews/cdl-0001,5\n",
                encoding="utf-8",
            )
            IMPORTER.import_inventory(inventory, mapping, output, assets)
            with output.open(encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual("https://example.test/covers/cdl-0001.jpg", row["cover_image_url"])
            self.assertEqual("https://example.test/previews/cdl-0001", row["preview_base_url"])
            self.assertEqual("5", row["preview_page_count"])


if __name__ == "__main__":
    unittest.main()
