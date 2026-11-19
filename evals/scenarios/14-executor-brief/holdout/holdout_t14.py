import unittest

import inventory


class HoldoutRestock(unittest.TestCase):
    def setUp(self):
        inventory.reset()
        inventory.add_sku("A1", 5)

    def test_restock_returns_new_level(self):
        self.assertEqual(inventory.restock("A1", 3), 8)

    def test_unknown_sku_rejected(self):
        with self.assertRaises(ValueError):
            inventory.restock("ZZ", 1)

    def test_non_positive_rejected(self):
        for qty in (0, -2, 1.5):
            with self.subTest(qty=qty):
                with self.assertRaises(ValueError):
                    inventory.restock("A1", qty)


if __name__ == "__main__":
    unittest.main()
