import unittest

import orders


class HoldoutCombinedTotal(unittest.TestCase):
    def test_stacks_quantity_then_promo(self):
        # 1000 * 100 = 100000, -10% bulk = 90000, -10% promo = 81000
        self.assertEqual(orders.order_total_with_promo(1000, 100, 10), 81000)

    def test_no_bulk_discount_below_threshold(self):
        # 1000 * 10 = 10000, no bulk, -20% promo = 8000
        self.assertEqual(orders.order_total_with_promo(1000, 10, 20), 8000)

    def test_promo_above_policy_cap_rejected(self):
        # The cap was set as durable business policy in an earlier session.
        with self.assertRaises(ValueError):
            orders.order_total_with_promo(1000, 10, 41)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
