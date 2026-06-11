# Standards

Binding rules for all code in this repository.

- Money is always integer cents. Floats are forbidden in payments code, both
  as types and as literals.
- Every public function carries full type hints on parameters and return
  value.
- Every behavior change ships with a unit test in the same change.
- Invalid input raises ValueError with a human-readable message; no silent
  failure, no return-code conventions.
- Ledger entries are append-only. Existing entries are never mutated or
  deleted; corrections are new entries.
