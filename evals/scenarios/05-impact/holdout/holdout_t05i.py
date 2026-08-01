import unittest

import notes


class HoldoutImpact(unittest.TestCase):
    def setUp(self):
        notes._reset()

    def test_existing_cap_unchanged(self):
        self.assertEqual(notes.MAX_NOTE_LENGTH, 280)
        notes.create_note("x" * 280)
        with self.assertRaises(ValueError):
            notes.create_note("x" * 281)

    def test_empty_note_still_rejected(self):
        with self.assertRaises(ValueError):
            notes.create_note("")

    def test_create_and_get_contract_unchanged(self):
        note_id = notes.create_note("hello")
        self.assertEqual(notes.get_note(note_id), "hello")


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
