# Client Domain

The client module (`client.py`) wraps a caller-supplied fetch function with
retry behavior. The client retries failed requests up to 5 times with a fixed
1 second delay between attempts. All exceptions trigger a retry.

Invariants:

- Retry tuning lives in module constants (see [../standards.md](../standards.md)).
- The fetch function is treated as opaque; the client never inspects its
  result beyond returning it.
