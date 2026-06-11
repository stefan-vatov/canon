---
sources: [inventory.py]
verified: 0000000
---
# Inventory Domain

The inventory module (`inventory.py`) tracks per-sku stock levels and
accumulates reservations. `set_stock` overwrites a sku's level; `reserve`
validates the quantity and adds to the sku's reservation total; `reserved`
and `stock_level` are read accessors. `_reset()` exists only for tests.

Invariants:

- Quantities are positive integers; invalid input raises ValueError (see
  [../standards.md](../standards.md)).
