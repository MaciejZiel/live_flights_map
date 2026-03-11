from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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
            base_timestamp = datetime.now(timezone.utc) - timedelta(minutes=90)
            snapshot_timestamps = [
                base_timestamp,
                base_timestamp + timedelta(minutes=30),
                base_timestamp + timedelta(minutes=60),
            ]

            for timestamp in snapshot_timestamps:
                service.store_snapshot(
                    {
                        "fetched_at": timestamp.isoformat(),
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
                end_at=(base_timestamp + timedelta(minutes=45)).isoformat(),
            )

            self.assertEqual(payload["count"], 2)
            self.assertEqual(payload["end_at"], (base_timestamp + timedelta(minutes=45)).isoformat())
            self.assertEqual(payload["snapshots"][0]["fetched_at"], snapshot_timestamps[0].isoformat())
            self.assertEqual(payload["snapshots"][1]["fetched_at"], snapshot_timestamps[1].isoformat())


if __name__ == "__main__":
    unittest.main()
