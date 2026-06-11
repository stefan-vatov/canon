# Payments Domain

The payments module (`payments.py`) keeps an in-memory, append-only ledger of
entries. `charge(amount_cents)` validates that the amount is a positive
integer, appends a charge entry, and returns its id. Ids are assigned
sequentially starting at 1. `balance_cents()` reports charges minus all other
entry kinds. `ledger()` returns a defensive copy; callers can never mutate
internal state through it.

Invariants:

- Amounts are integer cents (see [../glossary.md](../glossary.md)).
- The ledger is append-only (see [../standards.md](../standards.md)).
- `_reset()` exists only for tests and clears all state.
