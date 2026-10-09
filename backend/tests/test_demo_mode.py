from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest.mock import patch

import requests

from backend import create_app
from backend.config import Config
from backend.demo import DemoSnapshotCollector, SlidingWindowRateLimiter


class RateLimiterTests(unittest.TestCase):
    def test_limits_each_client_within_the_window(self) -> None:
        now = [100.0]
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60, clock=lambda: now[0])

        self.assertEqual(limiter.check("a"), (True, 0))
        self.assertEqual(limiter.check("a"), (True, 0))
        allowed, retry_after = limiter.check("a")
        self.assertFalse(allowed)
        self.assertEqual(retry_after, 60)
        self.assertTrue(limiter.check("b")[0])

        now[0] = 161.0
        self.assertTrue(limiter.check("a")[0])


def _demo_config(directory: str, **overrides):
    attributes = {
        "DEMO_MODE": True,
        "FLIGHT_DATA_PROVIDERS": ("demo",),
        "DEMO_FLIGHT_COUNT": 120,
        "DEMO_BACKGROUND_COLLECTOR": False,
        "DEMO_RATE_LIMIT_PER_MINUTE": 1000,
        "FLIGHT_ARCHIVE_PATH": os.path.join(directory, "history.sqlite3"),
        "WORKSPACE_DB_PATH": os.path.join(directory, "workspace.sqlite3"),
        "AIRCRAFT_PHOTO_CACHE_PATH": os.path.join(directory, "photos.sqlite3"),
        "OPENSKY_CACHE_PATH": os.path.join(directory, "provider-cache.json"),
        "AIRPORT_CATALOG_CACHE_PATH": os.path.join(directory, "airports.csv"),
        "FRONTEND_DIST_PATH": None,
        "CORS_ALLOWED_ORIGIN": "*",
    }
    attributes.update(overrides)
    return type("DemoTestConfig", (Config,), attributes)()


class DemoAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # Demo mode must not contact flight, route or photo providers. The only
        # outbound request allowed is the public-domain OurAirports catalog.
        self.requested_urls: list[str] = []

        def blocked_request(_session, method, url, *args, **kwargs):
            self.requested_urls.append(str(url))
            raise requests.ConnectionError("network disabled in tests")

        network_guard = patch("requests.Session.request", autospec=True, side_effect=blocked_request)
        network_guard.start()
        self.addCleanup(network_guard.stop)
        self.addCleanup(self._assert_only_allowed_hosts)

    def _assert_only_allowed_hosts(self) -> None:
        unexpected = [url for url in self.requested_urls if "ourairports" not in url]
        self.assertEqual(unexpected, [])

    def _app(self, **overrides):
        return create_app(_demo_config(self._tmp.name, **overrides))

    def test_api_is_read_only_and_stream_is_disabled(self) -> None:
        client = self._app().test_client()

        put = client.put("/api/workspace/state", json={"state": {}})
        post = client.post("/api/alerts/deliver", json={"url": "http://169.254.169.254/"})
        stream = client.get("/api/flights/stream")

        self.assertEqual(put.status_code, 403)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(stream.status_code, 404)
        self.assertEqual(put.headers["X-Demo-Mode"], "synthetic")

    def test_rate_limit_returns_429_with_retry_after(self) -> None:
        client = self._app(DEMO_RATE_LIMIT_PER_MINUTE=2).test_client()

        statuses = [client.get("/api/search?q=DEMO").status_code for _ in range(3)]

        self.assertEqual(statuses[:2], [200, 200])
        self.assertEqual(statuses[2], 429)
        self.assertIn("Retry-After", client.get("/api/search?q=DEMO").headers)

    def test_collected_snapshot_is_served_and_labelled_synthetic(self) -> None:
        app = self._app()
        runtime_collector = app.extensions["snapshot_collector_service"]
        archive = app.extensions["flight_archive_service"]
        provider = app.extensions["flight_details_service"].route_client.provider
        collector = DemoSnapshotCollector(
            type("Runtime", (), {"flight_archive_service": archive, "snapshot_collector_service": runtime_collector})(),
            provider,
            interval_seconds=60,
            backfill_minutes=10,
        )
        self.assertEqual(collector.backfill(), 10)
        result = collector.collect_once()
        self.assertEqual(result["sectors_synced"], 1)

        client = app.test_client()
        flights = client.get("/api/flights?lamin=-90&lamax=90&lomin=-180&lomax=180").get_json()
        self.assertEqual(flights["count"], 120)
        self.assertTrue(flights["meta"]["demo"]["synthetic"])

        replay = client.get("/api/history/replay?lamin=-90&lamax=90&lomin=-180&lomax=180&minutes=30").get_json()
        self.assertGreaterEqual(len(replay["snapshots"]), 10)
        viewport = client.get("/api/history/replay?lamin=34&lamax=72&lomin=-25&lomax=45&minutes=30").get_json()
        self.assertGreaterEqual(len(viewport["snapshots"]), 10)
        self.assertLess(viewport["snapshots"][-1]["count"], 120)

        flight = flights["flights"][0]
        details = client.get(f"/api/flights/{flight['icao24']}/details?callsign={flight['callsign']}").get_json()
        self.assertEqual(details["route"]["airline_name"], "Synthetic Demo Air")
        self.assertIsNone(details["photo"])

        health = client.get("/health").get_json()
        self.assertTrue(health["demo_mode"])

    def test_background_collector_backfills_on_start(self) -> None:
        app = self._app(DEMO_BACKGROUND_COLLECTOR=True, DEMO_BACKFILL_MINUTES=5, DEMO_SNAPSHOT_INTERVAL_SECONDS=60)
        collector = app.extensions["demo_snapshot_collector"]
        self.addCleanup(collector.stop)

        client = app.test_client()
        deadline = time.monotonic() + 10
        count = 0
        while time.monotonic() < deadline:
            payload = client.get("/api/flights?lamin=-90&lamax=90&lomin=-180&lomax=180").get_json()
            count = payload.get("count", 0)
            if count:
                break
            time.sleep(0.1)
        self.assertEqual(count, 120)


if __name__ == "__main__":
    unittest.main()
