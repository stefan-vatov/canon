import unittest

import reports


class TestReportHeader(unittest.TestCase):
    def test_header(self):
        self.assertEqual(reports.report_header("Daily"), "=== Daily ===")

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            reports.report_header("")


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
