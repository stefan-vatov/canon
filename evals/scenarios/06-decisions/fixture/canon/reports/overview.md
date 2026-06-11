---
sources: [reports.py]
verified: baseline
---
# Reports Domain

The reports module (`reports.py`) provides helpers for assembling plain-text
reports. `report_header(title)` validates the title and returns the framed
header line.

Invariants:

- Invalid input raises ValueError (see [../standards.md](../standards.md)).
