import unittest

import inventory


class TestInventory(unittest.TestCase):
    def setUp(self):
        inventory._reset()

    def test_set_and_read_stock(self):
        inventory.set_stock("widget", 10)
        self.assertEqual(inventory.stock_level("widget"), 10)

    def test_reserve_accumulates(self):
        inventory.set_stock("widget", 10)
        inventory.reserve("widget", 2)
        inventory.reserve("widget", 3)
        self.assertEqual(inventory.reserved("widget"), 5)

    def test_rejects_non_positive_qty(self):
        with self.assertRaises(ValueError):
            inventory.reserve("widget", 0)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
