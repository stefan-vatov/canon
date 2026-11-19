"""In-process stock levels keyed by sku."""

_stock: dict[str, int] = {}


def reset() -> None:
    """Forget every sku (used by tests)."""
    _stock.clear()


def add_sku(sku: str, level: int) -> None:
    """Register a new sku with its starting stock level."""
    if not isinstance(sku, str) or not sku:
        raise ValueError("sku must be a non-empty string")
    if sku in _stock:
        raise ValueError(f"sku {sku!r} already exists")
    if not isinstance(level, int) or isinstance(level, bool) or level < 0:
        raise ValueError("level must be a non-negative integer")
    _stock[sku] = level


def level(sku: str) -> int:
    """Current stock level of an existing sku."""
    if sku not in _stock:
        raise ValueError(f"unknown sku {sku!r}")
    return _stock[sku]
