import unittest

import orders


class HoldoutPromoPolicy(unittest.TestCase):
    def test_max_allowed_discount_accepted(self):
        self.assertEqual(orders.apply_promo(1000, 40), 600)

    def test_above_max_rejected(self):
        with self.assertRaises(ValueError):
            orders.apply_promo(1000, 41)

    def test_rounds_down_to_integer_cents(self):
        result = orders.apply_promo(999, 10)
        self.assertEqual(result, 899)
        self.assertIsInstance(result, int)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
