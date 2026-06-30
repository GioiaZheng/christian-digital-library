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
        self.assertEqual("天道注释：出埃及记卷上", title)
        self.assertEqual("赖建国", author)

    def test_multi_number_bible_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/09 10圣经信息系列 撒母耳记上下.zip")
        self.assertEqual("圣经信息系列 撒母耳记上下", title)
        self.assertEqual("", author)

    def test_long_catalog_number_and_page_marker_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/10156162_新约的传说_p258.zip")
        self.assertEqual("新约的传说", title)
        self.assertEqual("", author)

    def test_long_catalog_number_without_separator_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/13075753今日如何读新约.zip")
        self.assertEqual("今日如何读新约", title)
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

    def test_real_count_title_number_is_kept(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/100名画旧约.zip")
        self.assertEqual("100名画旧约", title)
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

    def test_catalog_m_code_prefix_and_english_author_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/M6158 旧约神学 当代争论的基本议题 Gerhard Hasel.zip"
        )
        self.assertEqual("旧约神学：当代争论的基本议题", title)
        self.assertEqual("Gerhard Hasel", author)

    def test_catalog_m_code_prefix_and_chinese_author_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/M6164 圣经结构式注释 以弗所书 李保罗博士.zip"
        )
        self.assertEqual("圣经结构式注释：以弗所书", title)
        self.assertEqual("李保罗", author)

    def test_catalog_m_code_prefix_with_subtitle_and_author_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/M6215 圣灵降临-由新约看圣灵的恩赐 葛富恩（Richard B. Gaffin,Jr.）.zip"
        )
        self.assertEqual("圣灵降临：由新约看圣灵的恩赐", title)
        self.assertEqual("葛富恩 Richard B Gaffin Jr", author)

    def test_single_letter_catalog_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/R認識聖經文學--郭秀娟.zip")
        self.assertEqual("認識聖經文學", title)
        self.assertEqual("郭秀娟", author)

    def test_lowercase_catalog_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/x06罗马书释经讲道-刘道顺.zip")
        self.assertEqual("罗马书释经讲道", title)
        self.assertEqual("刘道顺", author)

    def test_catalog_prefix_with_bible_series_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/19校园_威尔克-诗篇下 圣经信息系列.zip"
        )
        self.assertEqual("圣经信息系列：诗篇下", title)
        self.assertEqual("威尔克", author)

    def test_alpha_volume_catalog_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/1A 创世记 上 约翰 华尔顿.zip")
        self.assertEqual("创世记：上", title)
        self.assertEqual("约翰 华尔顿", author)

    def test_alpha_volume_catalog_prefix_for_exodus_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/2B 出埃及记 下 彼得 恩斯.zip")
        self.assertEqual("出埃及记：下", title)
        self.assertEqual("彼得 恩斯", author)

    def test_combined_volume_prefix_before_series_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/31+34+36圣经信息系列：俄巴底亚书、那鸿书、西番雅书.zip"
        )
        self.assertEqual("圣经信息系列：俄巴底亚书、那鸿书、西番雅书", title)
        self.assertEqual("", author)

    def test_combined_volume_prefix_with_author_and_trailing_series_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/51+57歌罗西书、腓利门书：路卡斯：圣经信息系列.zip"
        )
        self.assertEqual("圣经信息系列：歌罗西书、腓利门书", title)
        self.assertEqual("路卡斯", author)

    def test_combined_comma_volume_prefix_before_series_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/60,61,65天道研经—彼犹.zip")
        self.assertEqual("天道研经：彼犹", title)
        self.assertEqual("", author)

    def test_combined_comma_volume_prefix_with_author_after_series_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/60,61,65天道研经—彼犹--冯国泰、李汤马.zip")
        self.assertEqual("天道研经：彼犹", title)
        self.assertEqual("冯国泰 李汤马", author)

    def test_spaced_double_number_prefix_before_series_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/12 18 天道研经――歌罗西书、腓利门书_冯国泰.zip")
        self.assertEqual("天道研经：歌罗西书、腓利门书", title)
        self.assertEqual("冯国泰", author)

    def test_trailing_duplicate_marker_after_series_author_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/天道研经_帖前后_华约翰_2.zip")
        self.assertEqual("天道研经：帖前后", title)
        self.assertEqual("华约翰", author)

    def test_parenthetical_series_after_number_prefix_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/54+56提摩太前书、提多书(圣经信息系列).zip")
        self.assertEqual("圣经信息系列：提摩太前书、提多书", title)
        self.assertEqual("", author)

    def test_malformed_parenthetical_series_after_number_prefix_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/31、32俄巴底亚书、约拿书（天道研经导读}.zip")
        self.assertEqual("天道研经导读：俄巴底亚书、约拿书", title)
        self.assertEqual("", author)

    def test_fullwidth_dash_series_middle_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/62+63+64约翰书信－生命信息系列－杰克曼.zip")
        self.assertEqual("生命信息系列：约翰书信", title)
        self.assertEqual("杰克曼", author)

    def test_spaced_lesson_number_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/42 伟大的教师耶稣.zip")
        self.assertEqual("伟大的教师耶稣", title)
        self.assertEqual("", author)

    def test_tiandao_commentary_parts_are_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/51教牧书信--张永信--天道注释.zip")
        self.assertEqual("天道注释：教牧书信", title)
        self.assertEqual("张永信", author)

    def test_tiandao_commentary_with_letter_prefix_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/Y雅歌@---黄朱伦---天道圣经注释.zip")
        self.assertEqual("天道圣经注释：雅歌", title)
        self.assertEqual("黄朱伦", author)

    def test_tiandao_commentary_with_mixed_traditional_suffix_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/Y雅歌@---黃朱倫---天道聖經注釋.zip")
        self.assertEqual("天道聖經注釋：雅歌", title)
        self.assertEqual("黃朱倫", author)

    def test_eb_catalog_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/EB0046 新约书卷详纲 - 马有藻.zip")
        self.assertEqual("新约书卷详纲", title)
        self.assertEqual("马有藻", author)

    def test_acts_commentary_volume_and_author_are_split(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/使徒行传注释，卷一，加尔文.zip")
        self.assertEqual("使徒行传注释：卷一", title)
        self.assertEqual("加尔文", author)

    def test_acts_commentary_trailing_book_noise_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/M5960 使徒行传注解（下册）徒 黄迦勒.zip")
        self.assertEqual("使徒行传注解(下册)", title)
        self.assertEqual("黄迦勒", author)

    def test_traditional_acts_page_range_suffix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/使徒行傳Acts.1(444-470).zip")
        self.assertEqual("使徒行傳", title)
        self.assertEqual("", author)

    def test_traditional_acts_commentary_number_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/使徒行傳註釋1.zip")
        self.assertEqual("使徒行傳註釋：1", title)
        self.assertEqual("", author)

    def test_nivac_suffix_series_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/出埃及記上NIVAC国际释经应用系列 (1).zip")
        self.assertEqual("NIVAC国际释经应用系列：出埃及記上", title)
        self.assertEqual("", author)

    def test_known_series_parts_without_catalog_prefix_are_normalized(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/出埃及记-莫德-圣经信息系列-台北:校园出版社，2012(1).zip"
        )
        self.assertEqual("圣经信息系列：出埃及记", title)
        self.assertEqual("莫德", author)

    def test_tiandao_commentary_parts_without_catalog_prefix_are_normalized(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/出埃及记卷上--赖建国--天道注释.zip")
        self.assertEqual("天道注释：出埃及记卷上", title)
        self.assertEqual("赖建国", author)

    def test_numeric_catalog_prefix_before_old_testament_title_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/2旧约历史书导论-David M.Howard Jr.zip")
        self.assertEqual("旧约历史书导论", title)
        self.assertEqual("David M Howard Jr", author)

    def test_nested_numeric_catalog_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/3-2随时候命 士师记.zip")
        self.assertEqual("随时候命：士师记", title)
        self.assertEqual("", author)

    def test_letter_suffix_catalog_prefix_before_study_series_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/3d研經系列.zip")
        self.assertEqual("研經系列", title)
        self.assertEqual("", author)

    def test_direct_numeric_prefix_before_fixed_title_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/3仁者无惧:路加福音.zip")
        self.assertEqual("仁者无惧：路加福音", title)
        self.assertEqual("", author)

    def test_direct_numeric_prefix_with_tail_author_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/67先知书2--何--注释--唐佑之-repaired.zip")
        self.assertEqual("先知书2：何：注释", title)
        self.assertEqual("唐佑之", author)

    def test_repeated_dot_catalog_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/46.47.哥林多前后書.zip")
        self.assertEqual("哥林多前后書", title)
        self.assertEqual("", author)

    def test_direct_numeric_prefix_before_sermon_title_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/16得胜凯歌 启示录.zip")
        self.assertEqual("得胜凯歌：启示录", title)
        self.assertEqual("", author)

    def test_direct_numeric_prefix_before_title_phrase_is_not_moved_to_author(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/6回归义路：罗马书.zip")
        self.assertEqual("回归义路：罗马书", title)
        self.assertEqual("", author)

    def test_ancient_christian_commentary_prefix_and_page_marker_are_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/66古代基督信仰圣经注释（新约-XIII-启）【748 P】.zip"
        )
        self.assertEqual("古代基督信仰圣经注释：新约：XIII：启", title)
        self.assertEqual("", author)

    def test_ancient_christian_commentary_space_format_is_normalized(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/28-39 古代基督信仰圣经注释 旧约-XIV-12先知书.zip"
        )
        self.assertEqual("古代基督信仰圣经注释：旧约：XIV：12先知书", title)
        self.assertEqual("", author)

    def test_ancient_christian_commentary_multi_number_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/6 7 8 9 10 古代基督信仰圣经注释(旧约:IV：书士得撒上下).zip"
        )
        self.assertEqual("古代基督信仰圣经注释：旧约：IV：书士得撒上下", title)
        self.assertEqual("", author)

    def test_ancient_christian_commentary_multi_number_prefix_without_last_space_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/6 7 8 9古代基督信仰圣经注释(旧约:IV：书士得撒上下).zip"
        )
        self.assertEqual("古代基督信仰圣经注释：旧约：IV：书士得撒上下", title)
        self.assertEqual("", author)

    def test_cambridge_church_history_duplicate_volume_prefix_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author("incoming/3剑桥基督教史第三卷.zip")
        self.assertEqual("剑桥基督教史第三卷", title)
        self.assertEqual("", author)

    def test_leading_volume_word_after_number_is_removed(self) -> None:
        title, author = IMPORTER.split_title_author(
            "incoming/《君王的使者——11篇以基督为中心的释经讲章》编著：陈若愚.zip"
        )
        self.assertEqual("以基督为中心的释经讲章", title)
        self.assertEqual("君王的使者", author)

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
