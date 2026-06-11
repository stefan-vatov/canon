import unittest

import orders


class HoldoutQuantityDiscount(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(orders.quantity_discount(49), 0)
        self.assertEqual(orders.quantity_discount(50), 5)
        self.assertEqual(orders.quantity_discount(99), 5)
        self.assertEqual(orders.quantity_discount(100), 10)

    def test_returns_integer_percent(self):
        self.assertIsInstance(orders.quantity_discount(50), int)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
