"""Session expiry."""
from datetime import datetime, timedelta

SESSION_TIMEOUT_MINUTES = 30


def is_expired(last_seen: datetime, now: datetime) -> bool:
    """Whether a session last seen at last_seen has expired as of now."""
    if not isinstance(last_seen, datetime) or not isinstance(now, datetime):
        raise ValueError("last_seen and now must be datetimes")
    return now - last_seen >= timedelta(minutes=SESSION_TIMEOUT_MINUTES)
