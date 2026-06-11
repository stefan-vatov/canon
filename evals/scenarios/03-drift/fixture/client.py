"""HTTP client wrapper with retry."""

import time

MAX_RETRIES = 3
RETRY_DELAYS_SECONDS = (0.1, 0.2, 0.4)


def fetch_with_retry(fetch):
    """Call fetch(); on ConnectionError retry with exponential backoff.

    Makes up to MAX_RETRIES attempts in total. Only ConnectionError triggers
    a retry; any other exception propagates immediately.
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return fetch()
        except ConnectionError as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS_SECONDS[attempt])
    raise last_error
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
