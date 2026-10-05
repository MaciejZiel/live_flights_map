from __future__ import annotations

import unittest

from backend.entrypoints.collector import _next_delay_seconds


class CollectorRetryDelayTests(unittest.TestCase):
    def test_successful_collection_uses_regular_interval(self) -> None:
        self.assertEqual(_next_delay_seconds({"warnings": []}, 1200), 1200)

    def test_provider_retry_after_is_respected(self) -> None:
        payload = {"warnings": ["provider cooling down"], "sectors": [{"retry_after_seconds": 1800}]}
        self.assertEqual(_next_delay_seconds(payload, 1200), 1800)

    def test_short_retry_window_does_not_wait_full_poll_interval(self) -> None:
        payload = {"warnings": ["provider cooling down"], "sectors": [{"retry_after_seconds": 25}]}
        self.assertEqual(_next_delay_seconds(payload, 1200), 30)

    def test_failure_without_retry_after_retries_with_bounded_delay(self) -> None:
        payload = {"warnings": ["temporary error"], "sectors": []}
        self.assertEqual(_next_delay_seconds(payload, 1200), 60)


if __name__ == "__main__":
    unittest.main()
