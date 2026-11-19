import unittest

import pagination


class TestPageCount(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(pagination.page_count(100, 30), 4)

    def test_rejects_zero_page_size(self):
        with self.assertRaises(ValueError):
            pagination.page_count(10, 0)


class TestDefaultPageSize(unittest.TestCase):
    def test_default_page_size_is_fifty(self):
        self.assertEqual(pagination.default_page_size(), 50)


if __name__ == "__main__":
    unittest.main()
