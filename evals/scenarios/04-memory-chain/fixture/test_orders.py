import unittest

import orders


class TestOrderTotal(unittest.TestCase):
    def test_total(self):
        self.assertEqual(orders.order_total_cents(250, 4), 1000)

    def test_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            orders.order_total_cents(250, 0)

    def test_rejects_non_int_price(self):
        with self.assertRaises(ValueError):
            orders.order_total_cents(2.5, 4)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
