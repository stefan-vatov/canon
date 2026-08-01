---
status: normative
scope: [http-client]
validation: [test_client.py]
related: [../standards.md]
---
# Client Domain

Failed requests are retried up to 5 times with a fixed 1 second delay between
attempts. All exceptions trigger a retry.

## Invariants

- Retry tuning follows [project standards](../standards.md).
- Successful results pass through unchanged.
