import unittest

import inventory


class HoldoutOversellFix(unittest.TestCase):
    def setUp(self):
        inventory._reset()
        inventory.set_stock("widget", 5)

    def test_can_reserve_up_to_stock(self):
        inventory.reserve("widget", 3)
        inventory.reserve("widget", 2)
        self.assertEqual(inventory.reserved("widget"), 5)

    def test_cannot_exceed_stock(self):
        inventory.reserve("widget", 4)
        with self.assertRaises(ValueError):
            inventory.reserve("widget", 2)
        self.assertEqual(inventory.reserved("widget"), 4)

    def test_invalid_qty_still_rejected(self):
        with self.assertRaises(ValueError):
            inventory.reserve("widget", 0)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
