# HTTP client retries

Failed requests are retried up to 5 times with a fixed 1 second delay between
attempts. All exceptions trigger a retry. Successful results pass through
unchanged.
