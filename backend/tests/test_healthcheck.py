from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import create_app
from backend.config import Config


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
