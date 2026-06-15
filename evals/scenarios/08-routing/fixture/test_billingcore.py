import unittest

import billingcore


class TestLineTotal(unittest.TestCase):
    def test_total(self):
        self.assertEqual(billingcore.line_total_cents(250, 4), 1000)

    def test_rejects_zero(self):
        with self.assertRaises(ValueError):
            billingcore.line_total_cents(250, 0)


if __name__ == "__main__":
    unittest.main()
