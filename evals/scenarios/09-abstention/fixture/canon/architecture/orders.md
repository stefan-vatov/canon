---
status: normative
scope: [orders]
validation: [test_orders.py]
related:
  - ../standards.md
  - ../decisions/dates-are-utc-date.md
---
# Orders Domain

Order dates are timezone-free UTC calendar dates. Unknown orders raise
`ValueError`.
