# Payments ledger

The ledger is append-only: a correction is a new entry, and existing entries
are never mutated or deleted, because finance reconciles its books against
entry ids and a changed entry breaks that reconciliation (owner). Callers get
defensive snapshots, so nothing outside the module can edit a stored entry.
