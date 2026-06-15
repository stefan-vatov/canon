---
sources: [billingcore.py]
verified: baseline
---
# Pricing Domain

The pricing module (`billingcore.py`) computes line totals and platform fees.
`line_total_cents(unit_price_cents, quantity)` returns the line total.

The platform fee is 250 basis points (2.5%) of a line total, rounded down to
whole cents. This is the only fee pricing applies; it is distinct from billing
late fees, tax, and any reporting rates.
