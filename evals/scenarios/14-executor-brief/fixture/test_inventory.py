import unittest

import inventory


class TestInventory(unittest.TestCase):
    def setUp(self):
        inventory.reset()

    def test_add_and_read(self):
        inventory.add_sku("A1", 5)
        self.assertEqual(inventory.level("A1"), 5)

    def test_unknown_sku(self):
        with self.assertRaises(ValueError):
            inventory.level("nope")


if __name__ == "__main__":
    unittest.main()
