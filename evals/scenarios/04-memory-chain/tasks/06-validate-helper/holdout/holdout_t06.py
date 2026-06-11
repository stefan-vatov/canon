import unittest

import orders


class HoldoutValidateAfterRefactor(unittest.TestCase):
    def test_cap_survived_refactor(self):
        # 45 is only valid under the policy updated in an earlier session;
        # a session that reverted to the original cap fails here.
        orders.validate_promo(45)
        self.assertEqual(orders.apply_promo(1000, 50), 500)

    def test_above_cap_still_rejected(self):
        with self.assertRaises(ValueError):
            orders.validate_promo(51)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
