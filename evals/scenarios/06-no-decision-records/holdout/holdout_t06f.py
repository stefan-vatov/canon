import unittest
from datetime import datetime, timedelta, timezone

import reports


class HoldoutFinal(unittest.TestCase):
    def test_utc_decision_survived_both_sessions(self):
        dt = datetime(2026, 6, 7, 8, 9, 10, tzinfo=timezone(timedelta(hours=-5)))
        self.assertEqual(reports.format_timestamp(dt), "2026-06-07T13:09:10Z")


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
