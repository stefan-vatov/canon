"""Append-only journal of postings; balances are derived, never stored."""

_journal: list[tuple[str, int]] = []


def reset() -> None:
    """Forget every posting (used by tests)."""
    _journal.clear()


def post(account: str, amount: int) -> None:
    """Append one posting to the journal."""
    if not isinstance(account, str) or not account:
        raise ValueError("account must be a non-empty string")
    _journal.append((account, amount))


def balance(account: str) -> int:
    """Sum of every posting to account."""
    return sum(value for name, value in _journal if name == account)
