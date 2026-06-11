---
sources: [notes.py]
verified: 0000000
---
# Notes Domain

The notes module (`notes.py`) stores plain-text notes in memory. Notes are
capped at 100 characters; longer text raises ValueError. `create_note`
returns the new note's id; `get_note` retrieves by id. `_reset()` exists
only for tests.

Invariants:

- Validation limits live in module constants (see [../standards.md](../standards.md)).
- Note ids are stable for the lifetime of the process.
