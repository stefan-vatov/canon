---
status: normative
scope: [reporting]
validation: [test_reports.py]
related: [../standards.md]
---
# Reports Domain

Reports are plain text. Titles are non-empty strings and report headers frame
the title using the active formatting decision.

## Invariants

- Invalid input raises `ValueError`.
