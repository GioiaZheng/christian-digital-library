import unittest

from scripts.clean_catalog_data import clean_row, normalize_tags


class CleanCatalogDataTest(unittest.TestCase):
    def test_normalizes_and_enriches_subject_tags(self):
        tags = normalize_tags("丁道尔：彼得前书——新约圣经注释", "聖經;註釋;其他")
        self.assertEqual(tags, "注释;彼得前书;新约")

    def test_keeps_uncertain_existing_tag_without_guessing(self):
        self.assertEqual(normalize_tags("不可言说的言说", "语言哲学"), "语言哲学")

    def test_adds_clear_theological_subjects_from_title(self):
        self.assertEqual(normalize_tags("基督教末世论的含义", "基督"), "末世论")

    def test_repairs_parent_ing_time_split(self):
        row = {
            "id": "cdl-test",
            "clean_title": "2015:Q1 尽心认识神：6D 1-08 PARENT",
            "author": "ING TIME",
            "translator": "",
            "category": "other",
            "tags": "",
        }

        changed = clean_row(row)

        self.assertTrue(changed)
        self.assertEqual(row["clean_title"], "2015:Q1 尽心认识神：6D 1-08 PARENT-ING TIME")
        self.assertEqual(row["author"], "")
        self.assertEqual(row["category"], "spiritual-life")

    def test_repairs_known_chinese_title_author_swap(self):
        row = {
            "id": "cdl-005079",
            "clean_title": "4 Can I Know Gods Will",
            "author": "我能知道神的旨意吗 司布尔 CQ",
            "translator": "",
            "category": "other",
            "tags": "",
        }

        changed = clean_row(row)

        self.assertTrue(changed)
        self.assertEqual(row["clean_title"], "我能知道神的旨意吗")
        self.assertEqual(row["author"], "司布尔")
        self.assertEqual(row["category"], "spiritual-life")

    def test_removes_format_noise_from_title_and_people(self):
        row = {
            "id": "cdl-test",
            "clean_title": "30 33先知书1：摩、弥（单排版）",
            "author": "唐佑之 单排版",
            "translator": "单排版",
            "category": "other",
            "tags": "",
        }

        changed = clean_row(row)

        self.assertTrue(changed)
        self.assertEqual(row["clean_title"], "先知书1：摩、弥")
        self.assertEqual(row["author"], "唐佑之")
        self.assertEqual(row["translator"], "")
        self.assertEqual(row["category"], "bible-study")

    def test_moves_volume_noise_out_of_author_field(self):
        row = {
            "id": "cdl-test",
            "clean_title": "理性信仰",
            "author": "壹册 电子修订版",
            "translator": "",
            "category": "theology",
            "tags": "信仰",
        }

        changed = clean_row(row)

        self.assertTrue(changed)
        self.assertEqual(row["clean_title"], "理性信仰（壹册）")
        self.assertEqual(row["author"], "")

    def test_removes_nivac_prefix_and_tail_noise(self):
        row = {
            "id": "cdl-test",
            "clean_title": "NIVAC国际释经应用系列：創世記(卷上)NIVAC+Hebrews",
            "author": "",
            "translator": "",
            "category": "bible-study",
            "tags": "释经;創世記",
        }

        changed = clean_row(row)

        self.assertTrue(changed)
        self.assertEqual(row["clean_title"], "国际释经应用系列：創世記(卷上)")

    def test_normalizes_nivac_prefix_titles(self):
        row = {
            "id": "cdl-test",
            "clean_title": "NIVAC 帖前后注释",
            "author": "",
            "translator": "",
            "category": "bible-study",
            "tags": "注释",
        }

        changed = clean_row(row)

        self.assertTrue(changed)
        self.assertEqual(row["clean_title"], "帖撒罗尼迦前后书注释")

    def test_reclassifies_other_from_high_confidence_subject_tag(self):
        row = {
            "id": "cdl-test",
            "clean_title": "中国士绅反教的原因",
            "author": "吕实强",
            "translator": "",
            "category": "other",
            "tags": "中国教会史;近代史",
        }

        self.assertTrue(clean_row(row))
        self.assertEqual(row["category"], "church-history")

    def test_biblical_counseling_is_pastoral_not_bible_study(self):
        row = {
            "id": "cdl-test",
            "clean_title": "人是怎么改变的",
            "author": "大卫·鲍力生",
            "translator": "",
            "category": "other",
            "tags": "圣经辅导;生命改变;成圣",
        }

        self.assertTrue(clean_row(row))
        self.assertEqual(row["category"], "pastoral")

    def test_does_not_override_existing_reviewed_category(self):
        row = {
            "id": "cdl-test",
            "clean_title": "教会中的家庭事工",
            "author": "",
            "translator": "",
            "category": "pastoral",
            "tags": "家庭事工",
        }

        clean_row(row)
        self.assertEqual(row["category"], "pastoral")

    def test_does_not_treat_ordinary_creation_word_as_theology(self):
        row = {
            "id": "cdl-test",
            "clean_title": "创造真爱的五项修炼",
            "author": "",
            "translator": "",
            "category": "other",
            "tags": "创造论;两性关系",
        }

        clean_row(row)
        self.assertEqual(row["category"], "other")


if __name__ == "__main__":
    unittest.main()
