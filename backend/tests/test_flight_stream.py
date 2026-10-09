from __future__ import annotations

import itertools
import unittest
from unittest.mock import Mock

from flask import Flask

from backend.routes.flights import _flight_stream_events, _snapshot_etag, api
from backend.services.provider_base import FlightProviderError

PAYLOAD = {
    "bbox": {"lamin": 50.0, "lamax": 51.0, "lomin": 19.0, "lomax": 20.0},
    "count": 0,
    "fetched_at": "2026-01-01T00:00:00Z",
    "flights": [],
    "meta": {"source": "collector_cache", "stale": False},
}


class FlightStreamEventTests(unittest.TestCase):
    def _frames(self, fetch, count, **kwargs):
        sleeps = []
        options = {"interval_seconds": 30, "heartbeat_seconds": 10, "sleep_fn": sleeps.append}
        options.update(kwargs)
        frames = list(itertools.islice(_flight_stream_events(fetch, **options), count))
        return frames, sleeps

    def test_first_frames_are_retry_hint_and_snapshot_with_etag_id(self) -> None:
        frames, _ = self._frames(lambda: PAYLOAD, 2)

        self.assertEqual(frames[0], "retry: 5000\n\n")
        self.assertTrue(frames[1].startswith(f"id: {_snapshot_etag(PAYLOAD)}\nevent: snapshot\n"))

    def test_heartbeats_are_sent_while_the_snapshot_is_unchanged(self) -> None:
        # retry, snapshot, then three heartbeats per 30 s interval (10 s each)
        # and no second snapshot because the payload did not change.
        frames, sleeps = self._frames(lambda: PAYLOAD, 8)

        self.assertEqual(frames[2:5], [": keep-alive\n\n"] * 3)
        self.assertEqual(sleeps[:3], [10, 10, 10])
        self.assertEqual(sum(frame.startswith("id:") for frame in frames), 1)
        self.assertEqual(frames[5:8], [": keep-alive\n\n"] * 3)

    def test_heartbeat_never_exceeds_the_poll_interval(self) -> None:
        _, sleeps = self._frames(lambda: PAYLOAD, 4, interval_seconds=5, heartbeat_seconds=60)

        self.assertEqual(sleeps[:2], [5, 5])

    def test_matching_last_event_id_skips_the_snapshot_the_client_already_has(self) -> None:
        frames, _ = self._frames(lambda: PAYLOAD, 3, last_event_id=_snapshot_etag(PAYLOAD))

        self.assertEqual(frames, ["retry: 5000\n\n", ": keep-alive\n\n", ": keep-alive\n\n"])

    def test_changed_snapshot_is_sent_again(self) -> None:
        payloads = iter([PAYLOAD, {**PAYLOAD, "count": 1}])
        frames, _ = self._frames(lambda: next(payloads), 6)

        snapshots = [frame for frame in frames if "event: snapshot" in frame]
        self.assertEqual(len(snapshots), 2)

    def test_provider_errors_become_upstream_error_events(self) -> None:
        def failing_fetch():
            raise FlightProviderError("rate limited")

        frames, _ = self._frames(failing_fetch, 2)

        self.assertIn("event: upstream_error", frames[1])
        self.assertIn("rate limited", frames[1])


class FlightStreamRouteTests(unittest.TestCase):
    def test_stream_response_disables_proxy_buffering_and_transforms(self) -> None:
        app = Flask(__name__)
        app.config.update(
            CORS_ALLOWED_ORIGIN="*",
            MAP_DEFAULT_LAMIN=49.0,
            MAP_DEFAULT_LAMAX=55.0,
            MAP_DEFAULT_LOMIN=14.0,
            MAP_DEFAULT_LOMAX=24.0,
            FLIGHT_STREAM_INTERVAL_SECONDS=30,
            FLIGHT_STREAM_HEARTBEAT_SECONDS=10,
        )
        snapshot_service = Mock()
        snapshot_service.get_flights.return_value = PAYLOAD
        app.extensions["flight_snapshot_service"] = snapshot_service
        app.register_blueprint(api, url_prefix="/api")

        response = app.test_client().get(
            "/api/flights/stream?lamin=50&lamax=51&lomin=19&lomax=20",
            buffered=False,
        )
        try:
            first_chunks = list(itertools.islice(response.response, 2))
        finally:
            response.close()

        self.assertEqual(response.mimetype, "text/event-stream")
        self.assertEqual(response.headers["X-Accel-Buffering"], "no")
        self.assertIn("no-transform", response.headers["Cache-Control"])
        self.assertNotIn("Connection", response.headers)
        body = b"".join(chunk if isinstance(chunk, bytes) else chunk.encode() for chunk in first_chunks)
        self.assertIn(b"event: snapshot", body)


if __name__ == "__main__":
    unittest.main()
