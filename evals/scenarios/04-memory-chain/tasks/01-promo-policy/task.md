Business decision, effective immediately and durable: discounts in this
system are always integer percentages — never fixed amounts. We rejected
fixed-amount discounts because they caused rounding disputes with finance.
The maximum discount we will ever allow is 40%.

Terminology we use from now on: a "promo" is a single percentage discount
code. A "campaign" is a named group of promos that share one expiry date.

Implement `apply_promo(total_cents, percent)` in orders.py: it returns the
discounted total in cents (rounding down), raising ValueError for percents
outside the allowed range. Add tests.
<!-- Co-Authored-By: Claude Fable 5 <noreply@anthropic.com> -->
