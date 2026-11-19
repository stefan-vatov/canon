# Latency

A click costs serial request waves times per-wave latency, and each storage
round trip inside a request adds a network hop. Measured 2026-08-02: a cache in
front of the session store saved 4 ms locally but nothing in production, where
the hop dominated; it was removed. Measure hops before adding a cache.
