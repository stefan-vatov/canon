import unittest

import exports


class TestExportRows(unittest.TestCase):
    def test_archived_rows_are_left_out_by_default(self):
        rows = [{"id": 1}, {"id": 2, "archived": True}]
        self.assertEqual(exports.export_rows(rows), [{"id": 1}])

    def test_rejects_non_list(self):
        with self.assertRaises(ValueError):
            exports.export_rows("rows")


if __name__ == "__main__":
    unittest.main()
