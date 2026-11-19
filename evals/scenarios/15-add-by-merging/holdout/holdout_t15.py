import unittest

import ledger


class HoldoutCents(unittest.TestCase):
    def setUp(self):
        ledger.reset()

    def test_integer_cents_accepted(self):
        ledger.post("cash", 1250)
        self.assertEqual(ledger.balance("cash"), 1250)

    def test_non_integers_rejected(self):
        for amount in (12.5, 12.0, True, "12"):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    ledger.post("cash", amount)


if __name__ == "__main__":
    unittest.main()
