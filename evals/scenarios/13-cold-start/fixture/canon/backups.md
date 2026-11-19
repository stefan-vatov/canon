# Backups

A restore never replays an external side effect whose outcome is unknown; such
effects are quarantined for a person to resolve. Accepted gap: open sockets are
not closed during a restore (cost: stale notifications only); reopen when the
owner asks for zero-notification restores.
