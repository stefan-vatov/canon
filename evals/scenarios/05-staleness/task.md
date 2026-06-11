Add tagging to the notes module: `add_tag(note_id, tag)` attaches a tag to an
existing note, and `find_by_tag(tag)` returns the ids of all notes carrying
that tag. Tags are lowercase alphanumeric strings; anything else raises
ValueError. Add tests.
<!-- Co-Authored-By: Claude Fable 5 <noreply@anthropic.com> -->
