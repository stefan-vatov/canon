# Standards

Binding rules for all code in this repository.

- Money is always integer cents. Floats are forbidden in pricing code, both
  as types and as intermediate values.
- Every public function carries full type hints on parameters and return
  value.
- Every behavior change ships with a unit test in the same change.
- Invalid input raises ValueError with a human-readable message.
