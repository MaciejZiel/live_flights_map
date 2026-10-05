from __future__ import annotations

import unittest
import os
from unittest.mock import patch

from backend.entrypoints.collector import _default_interval_seconds, _next_delay_seconds


class CollectorRetryDelayTests(unittest.TestCase):
    def test_collector_uses_anonymous_safe_default_without_oauth(self) -> None:
        with patch.dict(os.environ, {"SNAPSHOT_COLLECTOR_INTERVAL_SECONDS": "", "OPENSKY_CLIENT_ID": "", "OPENSKY_CLIENT_SECRET": ""}):
            self.assertEqual(_default_interval_seconds(), 1200)

    def test_collector_uses_higher_free_quota_for_oauth_interval(self) -> None:
        with patch.dict(os.environ, {"SNAPSHOT_COLLECTOR_INTERVAL_SECONDS": "", "OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": "secret"}):
            self.assertEqual(_default_interval_seconds(), 180)

    def test_collector_interval_can_be_overridden(self) -> None:
        with patch.dict(os.environ, {"SNAPSHOT_COLLECTOR_INTERVAL_SECONDS": "300", "OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": "secret"}):
            self.assertEqual(_default_interval_seconds(), 300)

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
