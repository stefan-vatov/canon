import unittest

import textutil


class HoldoutSlugify(unittest.TestCase):
    def test_collapses_and_strips(self):
        self.assertEqual(textutil.slugify("  Hello, World!  "), "hello-world")

    def test_digits_kept(self):
        self.assertEqual(textutil.slugify("Release 2.0 -- final"), "release-2-0-final")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            textutil.slugify(42)


if __name__ == "__main__":
    unittest.main()
