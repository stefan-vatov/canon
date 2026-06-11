import unittest

import payments


class TestCharge(unittest.TestCase):
    def setUp(self):
        payments._reset()

    def test_charge_returns_id_and_updates_balance(self):
        cid = payments.charge(500)
        self.assertEqual(cid, 1)
        self.assertEqual(payments.balance_cents(), 500)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            payments.charge(0)

    def test_rejects_non_int(self):
        with self.assertRaises(ValueError):
            payments.charge("500")

    def test_ledger_is_a_copy(self):
        payments.charge(100)
        payments.ledger().clear()
        self.assertEqual(len(payments.ledger()), 1)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
