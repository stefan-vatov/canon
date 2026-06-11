"""In-memory payments ledger. All money amounts are integer cents."""

_LEDGER = []
_NEXT_ID = 1


def charge(amount_cents: int) -> int:
    """Record a charge and return its ledger entry id."""
    global _NEXT_ID
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise ValueError("amount_cents must be a positive integer")
    entry = {"id": _NEXT_ID, "kind": "charge", "amount_cents": amount_cents}
    _LEDGER.append(entry)
    _NEXT_ID += 1
    return entry["id"]


def balance_cents() -> int:
    """Net balance: charges minus refunds, in cents."""
    total = 0
    for entry in _LEDGER:
        if entry["kind"] == "charge":
            total += entry["amount_cents"]
        else:
            total -= entry["amount_cents"]
    return total


def ledger() -> list:
    """Snapshot copy of all ledger entries, oldest first."""
    return [dict(entry) for entry in _LEDGER]


def _reset() -> None:
    """Test helper: clear all ledger state."""
    global _NEXT_ID
    _LEDGER.clear()
    _NEXT_ID = 1
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
