from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.services.flight_archive import FlightArchiveService
from backend.services.snapshot_collector import SnapshotCollectorService


class _SnapshotServiceStub:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def get_flights(
        self,
        bbox: dict[str, float],
        *,
        prefer_latest_cache: bool = True,
        update_latest_cache: bool = True,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "bbox": bbox,
                "prefer_latest_cache": prefer_latest_cache,
                "update_latest_cache": update_latest_cache,
            }
        )
        return self.payload


class _TrafficIntelligenceStub:
    def enrich_flights(self, flights: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                **flight,
                "route_label": "WAW-LHR",
                "intelligence_updated_at": "2026-03-11T00:00:00+00:00",
            }
            for flight in flights
        ]


class SnapshotCollectorServiceTests(unittest.TestCase):
    def test_collect_once_stores_latest_positions_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_service = FlightArchiveService(
                archive_path=str(Path(temp_dir) / "history.sqlite3"),
                retention_hours=24,
                max_snapshots=100,
            )
            bbox = {"lamin": 50.0, "lamax": 54.0, "lomin": 18.0, "lomax": 22.0}
            snapshot_service = _SnapshotServiceStub(
                {
                    "count": 1,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "bbox": bbox,
                    "flights": [
                        {
                            "icao24": "abc123",
                            "callsign": "LOT123",
                            "registration": "SP-LVG",
                            "type_code": "B38M",
                            "latitude": 52.2,
                            "longitude": 21.0,
                            "on_ground": False,
                        }
                    ],
                }
            )
            service = SnapshotCollectorService(
                snapshot_service=snapshot_service,
                traffic_intelligence_service=_TrafficIntelligenceStub(),
                archive_service=archive_service,
                sectors=({"key": "poland_focus", "bbox": bbox},),
            )

            payload = service.collect_once()
            latest_payload = archive_service.list_latest_flights(
                bbox=bbox,
                max_age_seconds=300,
            )

            self.assertEqual(payload["sectors_synced"], 1)
            self.assertEqual(payload["latest_positions_stored"], 1)
            self.assertEqual(latest_payload["count"], 1)
            self.assertEqual(latest_payload["flights"][0]["route_label"], "WAW-LHR")
            self.assertFalse(snapshot_service.calls[0]["prefer_latest_cache"])
            self.assertFalse(snapshot_service.calls[0]["update_latest_cache"])


if __name__ == "__main__":
    unittest.main()
