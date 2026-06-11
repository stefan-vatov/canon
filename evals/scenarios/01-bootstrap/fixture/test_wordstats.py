import unittest

import wordstats


class TestWordCount(unittest.TestCase):
    def test_counts_words(self):
        self.assertEqual(wordstats.word_count("a b  c"), 3)

    def test_empty(self):
        self.assertEqual(wordstats.word_count(""), 0)


class TestLineCount(unittest.TestCase):
    def test_counts_lines(self):
        self.assertEqual(wordstats.line_count("a\nb\nc"), 3)

    def test_empty(self):
        self.assertEqual(wordstats.line_count(""), 0)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
