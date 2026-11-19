import unittest
from datetime import datetime, timedelta

import sessions


class TestIsExpired(unittest.TestCase):
    def test_expires_at_thirty_minutes(self):
        start = datetime(2026, 1, 1, 12, 0, 0)
        self.assertFalse(sessions.is_expired(start, start + timedelta(minutes=29)))
        self.assertTrue(sessions.is_expired(start, start + timedelta(minutes=30)))

    def test_rejects_non_datetime(self):
        with self.assertRaises(ValueError):
            sessions.is_expired("yesterday", datetime(2026, 1, 1))


if __name__ == "__main__":
    unittest.main()
