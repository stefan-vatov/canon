import unittest

import ledger


class TestLedger(unittest.TestCase):
    def setUp(self):
        ledger.reset()

    def test_balance_is_derived(self):
        ledger.post("cash", 100)
        ledger.post("cash", -40)
        self.assertEqual(ledger.balance("cash"), 60)


if __name__ == "__main__":
    unittest.main()
