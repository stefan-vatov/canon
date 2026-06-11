"""Cumulative holdout suite: every durable requirement from the ten sessions.

The agent never sees this file. Each assertion traces to knowledge stated in
exactly one session; passing here means it survived the rest of the chain.
"""
import unittest

import orders


class HoldoutFinal(unittest.TestCase):
    def test_promo_cap_is_current_policy(self):  # sessions 1 + 5
        self.assertEqual(orders.apply_promo(1000, 50), 500)
        with self.assertRaises(ValueError):
            orders.apply_promo(1000, 51)

    def test_promo_rounds_down_integer(self):  # session 1
        result = orders.apply_promo(999, 10)
        self.assertEqual(result, 899)
        self.assertIsInstance(result, int)

    def test_quantity_discount_thresholds(self):  # session 2
        self.assertEqual(orders.quantity_discount(49), 0)
        self.assertEqual(orders.quantity_discount(50), 5)
        self.assertEqual(orders.quantity_discount(100), 10)

    def test_format_cents(self):  # session 3
        self.assertEqual(orders.format_cents(1234), "$12.34")
        self.assertEqual(orders.format_cents(5), "$0.05")

    def test_combined_total_stacks_discounts(self):  # session 4
        self.assertEqual(orders.order_total_with_promo(1000, 100, 10), 81000)

    def test_validate_promo_helper(self):  # session 6
        orders.validate_promo(45)
        with self.assertRaises(ValueError):
            orders.validate_promo(51)

    def test_campaigns_carry_expiry(self):  # sessions 1 + 7
        import campaigns
        import inspect
        params = " ".join(inspect.signature(campaigns.create_campaign).parameters)
        source = inspect.getsource(campaigns)
        self.assertTrue("expir" in params.lower() or "expir" in source.lower(),
                        "campaign definition lost its shared expiry date")


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
