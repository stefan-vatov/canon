---
status: normative
scope: [inventory]
validation: [test_inventory.py]
related: [../standards.md]
---
# Inventory Domain

Inventory tracks a stock level and accumulated reservations for each SKU.
Setting stock replaces the recorded level. Reservation quantities are positive
integers.

## Invariants

- Invalid operations raise `ValueError`.
