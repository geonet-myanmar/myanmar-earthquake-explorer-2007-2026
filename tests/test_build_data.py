import unittest

from scripts.build_data import parse_page


class ArchiveParserTests(unittest.TestCase):
    def test_extracts_archive_fields_and_missing_values(self):
        html = """
        <table><tr onclick="window.open('/EQ123')">
          <td>2008-11-28 03:46:32<br><font>2008-11-27 20:46:32 UTC</font></td>
          <td>3.2</td><td>20.00</td><td>97.93</td><td>-</td><td>-</td>
          <td><span>ประเทศพม่า<br><font>Myanmar</font></span></td>
          <td><img src="images/icon_peq6.png"></td>
        </tr></table>เหตุการณ์ที่ 1 to 1 of 1
        """
        start, end, total, rows = parse_page(html)
        self.assertEqual((start, end, total), (1, 1, 1))
        self.assertEqual(rows[0]["id"], "123")
        self.assertEqual(rows[0]["time_utc"], "2008-11-27T20:46:32Z")
        self.assertEqual(rows[0]["time_thailand"], "2008-11-28T03:46:32+07:00")
        self.assertEqual((rows[0]["latitude"], rows[0]["longitude"]), (20, 97.93))
        self.assertIsNone(rows[0]["depth_km"])
        self.assertIsNone(rows[0]["phase_count"])
        self.assertEqual((rows[0]["region_th"], rows[0]["region_en"]), ("ประเทศพม่า", "Myanmar"))
        self.assertTrue(rows[0]["felt"])
        self.assertEqual(rows[0]["source_url"], "https://earthquake.tmd.go.th/EQ123")

    def test_rejects_missing_rows(self):
        with self.assertRaisesRegex(ValueError, "expected 1 rows"):
            parse_page("เหตุการณ์ที่ 1 to 1 of 1")


if __name__ == "__main__":
    unittest.main()
