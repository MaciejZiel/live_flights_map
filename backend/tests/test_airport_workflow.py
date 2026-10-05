from __future__ import annotations

import unittest

from backend.services.airport_workflow import AirportWorkflowService, MAX_AIRPORT_RESULTS


class _CatalogStub:
    def __init__(self) -> None:
        self.list_limit = None

    def list_airports_in_bbox(self, bbox, limit):
        self.list_limit = limit
        return []

    def get_catalog_status(self):
        return {"status": "ready", "source": "cache"}


class _TrafficStub:
    def __init__(self) -> None:
        self.list_limit = None

    def list_known_airports_in_bbox(self, bbox, limit):
        self.list_limit = limit
        return []


class AirportWorkflowTests(unittest.TestCase):
    def test_clamps_large_airport_requests_and_reports_catalog_status(self) -> None:
        catalog = _CatalogStub()
        traffic = _TrafficStub()
        service = AirportWorkflowService(catalog, traffic, snapshot_service=None)

        payload = service.list_airports(
            bbox={"lamin": 49, "lamax": 55, "lomin": 14, "lomax": 25},
            limit=50_000,
        )

        self.assertEqual(MAX_AIRPORT_RESULTS, catalog.list_limit)
        self.assertEqual(MAX_AIRPORT_RESULTS * 2, traffic.list_limit)
        self.assertEqual({"status": "ready", "source": "cache"}, payload["catalog"])
        self.assertEqual([], payload["airports"])

    def test_keeps_at_least_one_result_for_non_positive_internal_limit(self) -> None:
        catalog = _CatalogStub()
        traffic = _TrafficStub()
        service = AirportWorkflowService(catalog, traffic, snapshot_service=None)

        service.list_airports(bbox={}, limit=0)

        self.assertEqual(1, catalog.list_limit)
        self.assertEqual(2, traffic.list_limit)


if __name__ == "__main__":
    unittest.main()
