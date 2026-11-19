# Sync

The server is the authority for ordering. A CLI edit made offline carries the
version it was based on; the server rejects it when that version is stale, and
the CLI asks the user to merge instead of overwriting silently.
