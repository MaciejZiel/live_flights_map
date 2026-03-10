from __future__ import annotations

import unittest

from backend.services.entity_search import EntitySearchService


class _ArchiveStub:
    def search_recent_flights(self, query: str, limit: int, lookback_hours: float):
        return {
            "results": [
                {
                    "icao24": "48ad08",
                    "callsign": "LOT285",
                    "registration": "SP-LVQ",
                    "type_code": "B38M",
                    "origin_country": "Poland",
                }
            ]
        }


class _AirportCatalogStub:
    def search_airports(self, query: str, limit: int):
        return []

    def search_locations(self, query: str, limit: int):
        return []


class _TrafficIntelStub:
    def search_aircraft_profiles(self, query: str, limit: int, lookback_hours: float):
        return [
            {
                "entity_type": "aircraft",
                "entity_key": "48ad08",
                "icao24": "48ad08",
                "registration": "SP-LVQ",
                "callsign": "LOT285",
                "type_code": "B38M",
                "origin_country": "Poland",
            }
        ]

    def list_known_airports_in_bbox(self, bbox: dict[str, float], limit: int):
        return []

    def search_airlines(self, query: str, limit: int, lookback_hours: float):
        return []

    def search_routes(self, query: str, limit: int):
        return []


class EntitySearchServiceTests(unittest.TestCase):
    def test_search_includes_deduplicated_registration_group(self) -> None:
        service = EntitySearchService(
            archive_service=_ArchiveStub(),
            airport_catalog_service=_AirportCatalogStub(),
            traffic_intelligence_service=_TrafficIntelStub(),
            lookback_hours=6,
        )

        payload = service.search("SP-LVQ", limit=8)

        self.assertIn("registrations", payload["groups"])
        self.assertEqual(payload["groups"]["registrations"][0]["entity_type"], "registration")
        self.assertEqual(payload["groups"]["registrations"][0]["entity_key"], "SP-LVQ")
        self.assertEqual(len(payload["groups"]["registrations"]), 1)


if __name__ == "__main__":
    unittest.main()
