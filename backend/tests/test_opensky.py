from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

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

    def test_oauth_client_fetches_and_reuses_bearer_token(self) -> None:
        client = OpenSkyClient(
            base_url="https://opensky-network.org/api/states/all",
            username=None,
            password=None,
            timeout=1,
            max_retries=0,
            client_id="test-client",
            client_secret="test-secret",
        )
        token_response = Mock()
        token_response.json.return_value = {"access_token": "test-token", "expires_in": 1800}
        token_response.raise_for_status.return_value = None
        snapshot_response = Mock()
        snapshot_response.json.return_value = {"states": []}
        snapshot_response.headers = {"X-Rate-Limit-Remaining": "3996"}
        snapshot_response.raise_for_status.return_value = None

        with patch.object(client.session, "post", return_value=token_response) as post:
            with patch.object(client.session, "get", return_value=snapshot_response) as get:
                client.fetch_flights({"lamin": -90, "lamax": 90, "lomin": -180, "lomax": 180})
                client.fetch_flights({"lamin": -90, "lamax": 90, "lomin": -180, "lomax": 180})

        post.assert_called_once_with(
            client.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
            timeout=1,
        )
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer test-token"})
        self.assertEqual(client.last_rate_limit_remaining, 3996)

    def test_oauth_client_refreshes_a_rejected_bearer_token_once(self) -> None:
        client = OpenSkyClient(
            base_url="https://opensky-network.org/api/states/all",
            username=None,
            password=None,
            timeout=1,
            max_retries=0,
            client_id="test-client",
            client_secret="test-secret",
        )
        token_responses = []
        for token in ("old-token", "new-token"):
            response = Mock()
            response.json.return_value = {"access_token": token, "expires_in": 1800}
            response.raise_for_status.return_value = None
            token_responses.append(response)
        unauthorized = requests.Response()
        unauthorized.status_code = 401
        success = Mock()
        success.status_code = 200
        success.raise_for_status.return_value = None

        with patch.object(client.session, "post", side_effect=token_responses) as post:
            with patch.object(client.session, "get", side_effect=[unauthorized, success]) as get:
                result = client._request_snapshot({"lamin": -90, "lamax": 90, "lomin": -180, "lomax": 180})

        self.assertIs(result, success)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer new-token"})


if __name__ == "__main__":
    unittest.main()
