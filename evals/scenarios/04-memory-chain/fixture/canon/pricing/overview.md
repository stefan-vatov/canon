# Pricing Domain

The orders module (`orders.py`) computes order line totals.
`order_total_cents(unit_price_cents, quantity)` validates both inputs as
positive integers and returns their product in cents.

Invariants:

- Amounts are integer cents (see [../glossary.md](../glossary.md)).
- Invalid input raises ValueError (see [../standards.md](../standards.md)).
