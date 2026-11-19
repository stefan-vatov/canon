import unittest
from datetime import datetime, timedelta

import sessions


class HoldoutConfigurableTimeout(unittest.TestCase):
    START = datetime(2026, 1, 1, 12, 0, 0)

    def test_default_is_still_thirty_minutes(self):
        self.assertFalse(sessions.is_expired(self.START, self.START + timedelta(minutes=29)))
        self.assertTrue(sessions.is_expired(self.START, self.START + timedelta(minutes=30)))

    def test_tenant_timeout_is_honoured(self):
        later = self.START + timedelta(minutes=10)
        self.assertTrue(sessions.is_expired(self.START, later, timeout_minutes=5))
        self.assertFalse(sessions.is_expired(self.START, later, timeout_minutes=240))

    def test_out_of_range_timeout_rejected(self):
        for bad in (4, 241, 0, -30, 12.5, "30", True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    sessions.is_expired(self.START, self.START, timeout_minutes=bad)


if __name__ == "__main__":
    unittest.main()
