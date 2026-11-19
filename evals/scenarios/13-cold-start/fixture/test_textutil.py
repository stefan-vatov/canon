import unittest

import textutil


class TestTruncate(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(textutil.truncate("abc", 5), "abc")

    def test_long_text_cut(self):
        self.assertEqual(textutil.truncate("abcdef", 4), "abc…")


if __name__ == "__main__":
    unittest.main()
