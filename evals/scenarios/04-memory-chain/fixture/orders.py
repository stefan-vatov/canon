"""Order pricing. All money amounts are integer cents."""


def order_total_cents(unit_price_cents: int, quantity: int) -> int:
    """Total price for an order line."""
    if not isinstance(unit_price_cents, int) or unit_price_cents <= 0:
        raise ValueError("unit_price_cents must be a positive integer")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    return unit_price_cents * quantity
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
