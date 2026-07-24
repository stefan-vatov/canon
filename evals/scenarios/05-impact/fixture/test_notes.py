import unittest

import notes


class TestNotes(unittest.TestCase):
    def setUp(self):
        notes._reset()

    def test_create_and_get(self):
        note_id = notes.create_note("hello")
        self.assertEqual(notes.get_note(note_id), "hello")

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            notes.create_note("")

    def test_rejects_too_long(self):
        with self.assertRaises(ValueError):
            notes.create_note("x" * (notes.MAX_NOTE_LENGTH + 1))


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
