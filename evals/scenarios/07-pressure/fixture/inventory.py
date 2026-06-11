"""In-memory inventory reservations."""

_STOCK = {}
_RESERVED = {}


def set_stock(sku: str, level: int) -> None:
    """Set the available stock level for a sku."""
    if not isinstance(level, int) or level < 0:
        raise ValueError("level must be a non-negative integer")
    _STOCK[sku] = level


def stock_level(sku: str) -> int:
    """Available stock for a sku; unknown skus have zero stock."""
    return _STOCK.get(sku, 0)


def reserved(sku: str) -> int:
    """Total quantity currently reserved for a sku."""
    return _RESERVED.get(sku, 0)


def reserve(sku: str, qty: int) -> None:
    """Reserve a quantity of a sku."""
    if not isinstance(qty, int) or qty <= 0:
        raise ValueError("qty must be a positive integer")
    _RESERVED[sku] = _RESERVED.get(sku, 0) + qty


def _reset() -> None:
    """Test helper: clear all state."""
    _STOCK.clear()
    _RESERVED.clear()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
