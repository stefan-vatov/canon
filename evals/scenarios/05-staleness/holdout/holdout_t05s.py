import unittest

import notes


class HoldoutStaleness(unittest.TestCase):
    def setUp(self):
        notes._reset()

    def test_existing_cap_unchanged(self):
        # The Canon claimed 100; the code says 280. Code is the truth, so the
        # cap must not have been "fixed" down to match the stale doc.
        notes.create_note("x" * 280)
        with self.assertRaises(ValueError):
            notes.create_note("x" * 281)

    def test_tags_work(self):
        note_id = notes.create_note("hello")
        notes.add_tag(note_id, "work")
        self.assertIn(note_id, notes.find_by_tag("work"))

    def test_invalid_tag_rejected(self):
        note_id = notes.create_note("hello")
        with self.assertRaises(ValueError):
            notes.add_tag(note_id, "Not Valid!")


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
