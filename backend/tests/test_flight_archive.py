from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.flight_archive import FlightArchiveService


class FlightArchiveServiceTests(unittest.TestCase):
    def test_replay_snapshots_can_be_anchored_to_specific_end_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = FlightArchiveService(
                archive_path=str(Path(temp_dir) / "history.sqlite3"),
                retention_hours=24,
                max_snapshots=100,
            )
            bbox = {
                "lamin": 50.0,
                "lamax": 54.0,
                "lomin": 18.0,
                "lomax": 22.0,
            }

            for timestamp in (
                "2026-03-10T10:00:00+00:00",
                "2026-03-10T10:30:00+00:00",
                "2026-03-10T11:00:00+00:00",
            ):
                service.store_snapshot(
                    {
                        "fetched_at": timestamp,
                        "bbox": bbox,
                        "count": 1,
                        "flights": [
                            {
                                "icao24": "abc123",
                                "latitude": 52.2,
                                "longitude": 21.0,
                                "on_ground": False,
                            }
                        ],
                    }
                )

            payload = service.list_replay_snapshots(
                bbox=bbox,
                minutes=45,
                limit=10,
                end_at="2026-03-10T10:45:00+00:00",
            )

            self.assertEqual(payload["count"], 2)
            self.assertEqual(payload["end_at"], "2026-03-10T10:45:00+00:00")
            self.assertEqual(payload["snapshots"][0]["fetched_at"], "2026-03-10T10:00:00+00:00")
            self.assertEqual(payload["snapshots"][1]["fetched_at"], "2026-03-10T10:30:00+00:00")


if __name__ == "__main__":
    unittest.main()
