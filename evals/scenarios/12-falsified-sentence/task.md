Make the inactivity timeout configurable per tenant. Change `is_expired` in
sessions.py to `is_expired(last_seen, now, timeout_minutes=30)`. The timeout
must be an integer from 5 to 240 inclusive; anything else raises ValueError.
Add tests.
