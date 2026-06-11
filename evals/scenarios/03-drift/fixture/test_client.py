import unittest
from unittest import mock

import client


class TestFetchWithRetry(unittest.TestCase):
    def test_returns_first_success(self):
        self.assertEqual(client.fetch_with_retry(lambda: "ok"), "ok")

    @mock.patch("client.time.sleep")
    def test_three_attempts_then_raises(self, _sleep):
        calls = []

        def always_fails():
            calls.append(1)
            raise ConnectionError("down")

        with self.assertRaises(ConnectionError):
            client.fetch_with_retry(always_fails)
        self.assertEqual(len(calls), 3)

    def test_other_exceptions_propagate_immediately(self):
        calls = []

        def fails_differently():
            calls.append(1)
            raise ValueError("bad")

        with self.assertRaises(ValueError):
            client.fetch_with_retry(fails_differently)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
