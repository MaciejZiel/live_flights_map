from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.services.flight_snapshot import FlightSnapshotService


class _ProviderStub:
    def __init__(self, name: str, payload: dict[str, object]) -> None:
        self.name = name
        self.payload = payload
        self.calls = 0

    def fetch_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        self.calls += 1
        return self.payload


class FlightSnapshotServiceTests(unittest.TestCase):
    def test_adds_provider_and_quality_meta_to_live_snapshot(self) -> None:
        fetched_at = datetime.fromtimestamp(1000, timezone.utc).isoformat()
        provider = _ProviderStub(
            "adsb_lol",
            {
                "count": 4,
                "fetched_at": fetched_at,
                "bbox": {"lamin": 35.0, "lamax": 52.0, "lomin": 8.0, "lomax": 26.0},
                "flights": [
                    {
                        "icao24": "abc001",
                        "registration": "SP-LVG",
                        "type_code": "B38M",
                        "callsign": "LOT123",
                        "last_contact": 990,
                        "on_ground": False,
                    },
                    {
                        "icao24": "abc002",
                        "registration": "SP-LVH",
                        "type_code": "B38M",
                        "callsign": "LOT456",
                        "last_contact": 982,
                        "on_ground": False,
                    },
                    {
                        "icao24": "abc003",
                        "registration": None,
                        "type_code": "E75L",
                        "callsign": "DLH2AB",
                        "last_contact": 930,
                        "on_ground": True,
                    },
                    {
                        "icao24": "abc004",
                        "registration": "D-ABCD",
                        "type_code": None,
                        "callsign": None,
                        "last_contact": 910,
                        "on_ground": False,
                    },
                ],
            },
        )
        service = FlightSnapshotService(
            providers=[provider],
            cache_ttl=3600,
            cooldown_seconds=60,
        )

        payload = service.get_flights({"lamin": 35.0, "lamax": 52.0, "lomin": 8.0, "lomax": 26.0})

        self.assertEqual(payload["meta"]["provider_used"], "adsb_lol")
        self.assertEqual(payload["meta"]["providers_configured"], ["adsb_lol"])
        self.assertEqual(payload["meta"]["airspace_scope"], "regional")
        self.assertEqual(payload["meta"]["quality"]["identity"]["registration_pct"], 75)
        self.assertEqual(payload["meta"]["quality"]["identity"]["type_pct"], 75)
        self.assertEqual(payload["meta"]["quality"]["traffic"]["airborne"], 3)
        self.assertEqual(payload["meta"]["quality"]["traffic"]["ground"], 1)
        self.assertEqual(payload["meta"]["quality"]["traffic"]["fresh_contact_pct"], 50)
        self.assertIn("coverage", payload["meta"]["quality"]["summary"].lower())

    def test_cache_hit_preserves_last_live_provider_name(self) -> None:
        provider = _ProviderStub(
            "opensky",
            {
                "count": 1,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "bbox": {"lamin": 50.0, "lamax": 51.0, "lomin": 19.0, "lomax": 20.0},
                "flights": [
                    {
                        "icao24": "abc001",
                        "registration": "SP-LVG",
                        "type_code": "B38M",
                        "callsign": "LOT123",
                        "last_contact": datetime.now(timezone.utc).timestamp(),
                        "on_ground": False,
                    }
                ],
            },
        )
        service = FlightSnapshotService(
            providers=[provider],
            cache_ttl=3600,
            cooldown_seconds=60,
        )
        bbox = {"lamin": 50.0, "lamax": 51.0, "lomin": 19.0, "lomax": 20.0}

        live_payload = service.get_flights(bbox)
        cached_payload = service.get_flights(bbox)

        self.assertEqual(provider.calls, 1)
        self.assertEqual(live_payload["meta"]["source"], "live")
        self.assertEqual(cached_payload["meta"]["source"], "cache")
        self.assertEqual(cached_payload["meta"]["provider_used"], "opensky")


if __name__ == "__main__":
    unittest.main()
