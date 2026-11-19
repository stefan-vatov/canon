import unittest

import pagination


class H(unittest.TestCase):
    def test_clamps_to_current_default_100(self):
        self.assertEqual(pagination.clamp_page_size(500), 100)

    def test_passes_through_small(self):
        self.assertEqual(pagination.clamp_page_size(30), 30)

    def test_passes_through_values_above_retired_default(self):
        for requested in (51, 75, 99):
            with self.subTest(requested=requested):
                self.assertEqual(pagination.clamp_page_size(requested), requested)


if __name__ == "__main__":
    unittest.main()
