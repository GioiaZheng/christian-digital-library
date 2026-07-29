import unittest

from scripts.clean_catalog_data import clean_row


class CleanCatalogDataTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
