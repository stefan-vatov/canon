import unittest

import orders


class AbstentionHoldout(unittest.TestCase):
    def test_missing_policy_is_not_implemented(self):
        self.assertFalse(
            hasattr(orders, "within_refund_window"),
            "refund-window behavior requires an established policy",
        )


if __name__ == "__main__":
    unittest.main()
