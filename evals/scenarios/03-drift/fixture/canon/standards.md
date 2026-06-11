# Standards

Binding rules for all code in this repository.

- Retry tuning lives in module-level constants, never inline literals.
- Every behavior change ships with a unit test in the same change.
- Public functions document their retry and error semantics in docstrings.
