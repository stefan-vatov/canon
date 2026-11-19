# Notes

Note text is stored exactly as given and returned unchanged by id, because the
sync service and the export job both compare notes byte for byte. Invalid note
text is rejected at creation and never truncated, since a truncated note was
once quoted out of context in a customer dispute (owner).
