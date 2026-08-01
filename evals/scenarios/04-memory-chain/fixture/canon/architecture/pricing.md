---
status: normative
scope: [pricing]
validation: [test_orders.py]
related: [../standards.md]
---
# Pricing Domain

Order line totals use positive integer unit prices and quantities. The result
is their product in integer cents.

## Invariants

- Amounts are integer cents.
- Invalid input raises `ValueError`.
- Project-wide implementation rules live in [standards](../standards.md).
