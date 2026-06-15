import unittest

import billingcore


class HoldoutPlatformFee(unittest.TestCase):
    def test_fee_is_250_bps_rounded_down(self):
        # 2.5% of 10000 = 250 -> total 10250
        self.assertEqual(billingcore.apply_platform_fee(10000), 10250)

    def test_rounds_fee_down(self):
        # 999 * 250 // 10000 = 24 -> total 1023
        self.assertEqual(billingcore.apply_platform_fee(999), 1023)

    def test_not_a_distractor_rate(self):
        # 1500/800/500 bps would give 11500/10800/10500 — all wrong
        self.assertNotIn(billingcore.apply_platform_fee(10000),
                         (11500, 10800, 10500))


if __name__ == "__main__":
    unittest.main()
