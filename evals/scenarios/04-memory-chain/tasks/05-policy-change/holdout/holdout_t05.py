import unittest

import orders


class HoldoutNewCap(unittest.TestCase):
    def test_new_max_accepted(self):
        self.assertEqual(orders.apply_promo(1000, 50), 500)

    def test_above_new_max_rejected(self):
        with self.assertRaises(ValueError):
            orders.apply_promo(1000, 51)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
