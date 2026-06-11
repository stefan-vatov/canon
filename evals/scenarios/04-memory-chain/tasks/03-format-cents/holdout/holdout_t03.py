import unittest

import orders


class HoldoutFormatCents(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(orders.format_cents(1234), "$12.34")
        self.assertEqual(orders.format_cents(5), "$0.05")
        self.assertEqual(orders.format_cents(100), "$1.00")


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
