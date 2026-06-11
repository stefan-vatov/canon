Add `order_total_with_promo(unit_price_cents, quantity, promo_percent)` to
orders.py: compute the order total, apply the quantity discount for bulk
orders, then apply the promo on the result. Respect all existing business
policy. Add tests.
<!-- Co-Authored-By: Claude Fable 5 <noreply@anthropic.com> -->
