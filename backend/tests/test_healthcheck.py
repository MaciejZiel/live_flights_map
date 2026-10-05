from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from backend import create_app
from backend.config import Config
from backend.routes.flights import _provider_names_for_bbox, _snapshot_etag, _snapshot_response


class FlightRouteProviderSelectionTests(unittest.TestCase):
    def test_world_snapshot_uses_single_global_provider(self) -> None:
        world_bbox = {"lamin": -90.0, "lamax": 90.0, "lomin": -180.0, "lomax": 180.0}
        self.assertEqual(_provider_names_for_bbox(world_bbox), ("opensky",))

    def test_regional_snapshot_keeps_configured_provider_fallbacks(self) -> None:
        regional_bbox = {"lamin": 49.0, "lamax": 55.0, "lomin": 14.0, "lomax": 24.0}
        self.assertIsNone(_provider_names_for_bbox(regional_bbox))

    def test_snapshot_etag_ignores_runtime_cooldown_countdown(self) -> None:
        payload = {"fetched_at": "2026-01-01T00:00:00Z", "flights": [], "meta": {"provider_cooldowns": {"opensky": 20}}}
        changed_cooldown = {**payload, "meta": {"provider_cooldowns": {"opensky": 19}}}
        self.assertEqual(_snapshot_etag(payload), _snapshot_etag(changed_cooldown))

    def test_snapshot_response_returns_not_modified_for_matching_etag(self) -> None:
        app = Flask(__name__)
        payload = {"fetched_at": "2026-01-01T00:00:00Z", "flights": []}
        etag = _snapshot_etag(payload)
        with app.test_request_context(headers={"If-None-Match": f'"{etag}"'}):
            response = _snapshot_response(payload)
        self.assertEqual(response.status_code, 304)


class HealthcheckRouteTests(unittest.TestCase):
    def test_healthcheck_exposes_diagnostics_for_root_and_api_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = str(Path(temp_dir) / "history.sqlite3")
            workspace_path = str(Path(temp_dir) / "workspace.sqlite3")
            cache_path = str(Path(temp_dir) / "snapshot-cache.json")
            photo_cache_path = str(Path(temp_dir) / "photo-cache.sqlite3")
            with patch.multiple(
                Config,
                FLIGHT_ARCHIVE_PATH=archive_path,
                WORKSPACE_DB_PATH=workspace_path,
                OPENSKY_CACHE_PATH=cache_path,
                AIRCRAFT_PHOTO_CACHE_PATH=photo_cache_path,
                FLIGHT_DATA_PROVIDERS=("adsb_lol",),
            ):
                app = create_app()
                client = app.test_client()

            for route in ("/health", "/api/health"):
                response = client.get(route)
                self.assertEqual(response.status_code, 200)

                payload = response.get_json()
                self.assertIn(payload["status"], {"ok", "degraded"})
                self.assertIn("checked_at", payload)
                self.assertIn("services", payload)
                self.assertEqual(
                    payload["services"]["live_snapshot"]["providers"],
                    ["adsb_lol"],
                )
                self.assertTrue(payload["services"]["archive"]["file_present"])
                self.assertIn("collector", payload["services"])
                self.assertTrue(payload["services"]["workspace"]["file_present"])
                self.assertIn("aircraft_photos", payload["services"])
                self.assertTrue(payload["services"]["aircraft_photos"]["file_present"])


if __name__ == "__main__":
    unittest.main()
