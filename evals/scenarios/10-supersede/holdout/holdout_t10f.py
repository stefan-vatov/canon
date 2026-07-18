import unittest

import pagination


class H(unittest.TestCase):
    def test_current_default_survived_supersession(self):
        self.assertEqual(pagination.default_page_size(), 100)
        self.assertEqual(pagination.clamp_page_size(500), 100)

    def test_requests_above_retired_default_pass_through(self):
        for requested in (51, 75, 99):
            with self.subTest(requested=requested):
                self.assertEqual(pagination.clamp_page_size(requested), requested)


if __name__ == "__main__":
    unittest.main()
