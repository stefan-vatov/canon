---
status: normative
scope: [pagination]
validation: [test_pagination.py]
related: [../standards.md]
---
# Pagination

Page counts round up for positive integer totals and page sizes. Invalid input
raises `ValueError`.
