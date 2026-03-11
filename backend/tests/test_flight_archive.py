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

    def test_run_maintenance_prunes_old_snapshots(self) -> None:
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

            service.store_snapshot(
                {
                    "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
                    "bbox": bbox,
                    "count": 1,
                    "flights": [
                        {
                            "icao24": "old001",
                            "latitude": 52.2,
                            "longitude": 21.0,
                            "on_ground": False,
                        }
                    ],
                }
            )
            service.store_snapshot(
                {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "bbox": bbox,
                    "count": 1,
                    "flights": [
                        {
                            "icao24": "new001",
                            "latitude": 52.3,
                            "longitude": 21.1,
                            "on_ground": False,
                        }
                    ],
                }
            )
            service.retention_hours = 1

            maintenance = service.run_maintenance(vacuum=False)

            self.assertEqual(maintenance["snapshot_rows_before"], 2)
            self.assertEqual(maintenance["snapshot_rows_after"], 1)
            self.assertEqual(maintenance["snapshots_pruned"], 1)

    def test_latest_positions_cache_can_be_queried_by_bbox(self) -> None:
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
            service.store_latest_snapshot(
                {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "count": 2,
                    "flights": [
                        {
                            "icao24": "abc123",
                            "callsign": "LOT123",
                            "registration": "SP-LVG",
                            "type_code": "B38M",
                            "latitude": 52.2,
                            "longitude": 21.0,
                            "on_ground": False,
                            "route_label": "WAW-LHR",
                        },
                        {
                            "icao24": "def456",
                            "callsign": "DLH9AB",
                            "registration": "D-AIJP",
                            "type_code": "A320",
                            "latitude": 41.9,
                            "longitude": 12.5,
                            "on_ground": False,
                        },
                    ],
                },
                sector_key="europe",
            )

            payload = service.list_latest_flights(bbox=bbox, max_age_seconds=300)

            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["flights"][0]["icao24"], "abc123")
            self.assertEqual(payload["flights"][0]["route_label"], "WAW-LHR")
            self.assertEqual(payload["cache_meta"]["sector_keys"], ["europe"])

    def test_run_maintenance_prunes_stale_latest_positions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = FlightArchiveService(
                archive_path=str(Path(temp_dir) / "history.sqlite3"),
                retention_hours=24,
                max_snapshots=100,
            )
            service.store_latest_snapshot(
                {
                    "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
                    "count": 1,
                    "flights": [
                        {
                            "icao24": "old001",
                            "latitude": 52.2,
                            "longitude": 21.0,
                            "on_ground": False,
                        }
                    ],
                },
                sector_key="legacy",
            )
            service.retention_hours = 1

            maintenance = service.run_maintenance(vacuum=False)

            self.assertEqual(maintenance["latest_position_rows_before"], 1)
            self.assertEqual(maintenance["latest_position_rows_after"], 0)
            self.assertEqual(maintenance["latest_positions_pruned"], 1)


if __name__ == "__main__":
    unittest.main()
