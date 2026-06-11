"""In-memory note storage."""

MAX_NOTE_LENGTH = 280

_NOTES = []


def create_note(text: str) -> int:
    """Store a note and return its id."""
    if not isinstance(text, str) or not text:
        raise ValueError("text must be a non-empty string")
    if len(text) > MAX_NOTE_LENGTH:
        raise ValueError("text exceeds the maximum note length")
    _NOTES.append(text)
    return len(_NOTES) - 1


def get_note(note_id: int) -> str:
    """Return the text of a stored note."""
    return _NOTES[note_id]


def _reset() -> None:
    """Test helper: clear all state."""
    _NOTES.clear()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
