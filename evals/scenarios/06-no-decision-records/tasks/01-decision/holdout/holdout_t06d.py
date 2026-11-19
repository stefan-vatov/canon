import unittest
from datetime import datetime, timedelta, timezone

import reports


class HoldoutTimestampDecision(unittest.TestCase):
    def test_converts_to_utc_with_z(self):
        dt = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(reports.format_timestamp(dt), "2026-01-02T01:04:05Z")

    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            reports.format_timestamp(datetime(2026, 1, 2, 3, 4, 5))


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
