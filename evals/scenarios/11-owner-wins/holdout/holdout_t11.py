import unittest

import exports


class HoldoutOwnerWins(unittest.TestCase):
    ROWS = [{"id": 1}, {"id": 2, "archived": True}, {"id": 3, "archived": False}]

    def test_default_still_leaves_archived_rows_out(self):
        exported = exports.export_rows(self.ROWS)
        self.assertEqual([row["id"] for row in exported], [1, 3])

    def test_include_archived_exports_them_flagged(self):
        exported = exports.export_rows(self.ROWS, include_archived=True)
        self.assertEqual([row["id"] for row in exported], [1, 2, 3])
        self.assertIs(exported[1]["archived"], True)

    def test_invalid_rows_still_rejected(self):
        with self.assertRaises(ValueError):
            exports.export_rows(None, include_archived=True)


if __name__ == "__main__":
    unittest.main()
