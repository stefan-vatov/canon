Add `apply_platform_fee(line_total_cents)` to billingcore.py: it applies the
platform fee to a line total and returns the new total (line total plus fee),
in integer cents, rounding the fee down to whole cents. Use the platform fee
rate as defined in our Canon. Add a unit test.
<!-- Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com> -->
