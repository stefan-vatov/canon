import unittest
import datetime
import orders


class TestDaysBetween(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(
            orders.days_between(datetime.date(2026, 1, 1), datetime.date(2026, 1, 8)), 7)

    def test_negative(self):
        self.assertEqual(
            orders.days_between(datetime.date(2026, 1, 8), datetime.date(2026, 1, 1)), -7)


if __name__ == "__main__":
    unittest.main()
