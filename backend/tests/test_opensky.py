from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from backend.services.opensky import OpenSkyClient, OpenSkyRateLimitError


class OpenSkyClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = OpenSkyClient(
            base_url="https://opensky-network.org/api/states/all",
            username=None,
            password=None,
            timeout=1,
            max_retries=0,
        )

    def test_rate_limit_uses_opensky_retry_header(self) -> None:
        response = requests.Response()
        response.status_code = 429
        response.headers["X-Rate-Limit-Retry-After-Seconds"] = "1800"

        with patch.object(self.client.session, "get", return_value=response):
            with self.assertRaises(OpenSkyRateLimitError) as context:
                self.client._request_snapshot(
                    {"lamin": -90.0, "lamax": 90.0, "lomin": -180.0, "lomax": 180.0}
                )

        self.assertEqual(context.exception.retry_after_seconds, 1800.0)

    def test_rate_limit_falls_back_to_default_when_retry_header_is_missing(self) -> None:
        response = requests.Response()
        response.status_code = 429

        with patch.object(self.client.session, "get", return_value=response):
            with self.assertRaises(OpenSkyRateLimitError) as context:
                self.client._request_snapshot(
                    {"lamin": 50.0, "lamax": 51.0, "lomin": 19.0, "lomax": 20.0}
                )

        self.assertIsNone(context.exception.retry_after_seconds)


if __name__ == "__main__":
    unittest.main()
