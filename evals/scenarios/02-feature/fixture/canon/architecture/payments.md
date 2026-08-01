---
status: normative
scope: [payments]
validation: [test_payments.py]
related: [../standards.md]
---
# Payments Domain

Payments use an append-only ledger. Charges accept positive integer cents and
return stable, sequential entry ids. Balance is charges minus corrective
entries. Callers receive defensive ledger snapshots and cannot mutate stored
entries.

## Invariants

- Amounts are integer cents.
- Corrections create new entries; existing entries are never mutated or
  deleted.
- Invalid operations raise `ValueError`.
