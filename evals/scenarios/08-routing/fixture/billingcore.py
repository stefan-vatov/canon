"""Platform pricing primitives (module billingcore). All money is integer cents; rates are
integer basis points (bps); 100 bps = 1%."""


def line_total_cents(unit_price_cents: int, quantity: int) -> int:
    """Total for an order line."""
    if not isinstance(unit_price_cents, int) or unit_price_cents <= 0:
        raise ValueError("unit_price_cents must be a positive integer")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    return unit_price_cents * quantity
