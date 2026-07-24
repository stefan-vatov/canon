Refactor note-text validation into a new `note_validation.py` module.
`notes.create_note` must delegate validation before storing a note. Preserve
the complete public API and all existing behavior, including the 280-character
limit and exception behavior. Add or adjust tests for the extracted helper.
<!-- Co-Authored-By: Claude Fable 5 <noreply@anthropic.com> -->
