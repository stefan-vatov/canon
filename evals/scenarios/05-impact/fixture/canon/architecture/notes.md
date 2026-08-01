---
status: normative
scope: [notes]
validation: [test_notes.py]
related: [../standards.md]
---
# Notes Domain

Notes are non-empty strings capped at 280 characters. Creating a note returns
a stable process-local id; retrieval by that id returns the original text.

## Invariants

- Invalid note text raises `ValueError`.
- Note ids are stable for the lifetime of the process.
