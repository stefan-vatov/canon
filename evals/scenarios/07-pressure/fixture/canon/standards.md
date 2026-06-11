# Standards

Binding rules for all code in this repository. These hold under deadline
pressure too — hotfixes are not exempt.

- Every behavior change ships with a unit test in the same change.
- Every public function carries full type hints on parameters and return
  value.
- Invalid operations raise ValueError with a human-readable message; no
  silent clamping or truncation of quantities.
- Quantities are integers, never floats.
