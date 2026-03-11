from __future__ import annotations

import unittest

from backend.services.adsb_lol import ADSBLolClient


class _ResponseStub:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class _TiledADSBLolClient(ADSBLolClient):
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        super().__init__(
            base_url="https://example.invalid",
            timeout=1,
            max_retries=0,
            radius_limit_nm=250,
        )
        self._payloads = list(payloads)
        self.requests: list[tuple[float, float, int]] = []

    def _build_search_areas(self, bbox: dict[str, float]) -> list[tuple[float, float, int]]:
        return [
            (52.0, 21.0, 180),
            (53.0, 22.0, 180),
        ]

    def _request_snapshot(
        self,
        latitude: float,
        longitude: float,
        radius_nm: int,
    ) -> _ResponseStub:
        self.requests.append((latitude, longitude, radius_nm))
        return _ResponseStub(self._payloads.pop(0))


class ADSBLolClientTests(unittest.TestCase):
    def test_large_bbox_is_split_into_multiple_search_areas(self) -> None:
        client = ADSBLolClient(
            base_url="https://example.invalid",
            timeout=1,
            max_retries=0,
            radius_limit_nm=250,
        )

        search_areas = client._build_search_areas(
            {
                "lamin": 35.0,
                "lamax": 71.0,
                "lomin": -11.0,
                "lomax": 35.0,
            }
        )

        self.assertGreater(len(search_areas), 1)
        self.assertTrue(all(radius_nm <= 250 for _, _, radius_nm in search_areas))

    def test_fetch_flights_deduplicates_aircraft_across_search_areas(self) -> None:
        client = _TiledADSBLolClient(
            [
                {
                    "now": 1_000,
                    "ac": [
                        {
                            "hex": "abc123",
                            "lat": 52.2,
                            "lon": 21.0,
                            "alt_baro": 20000,
                            "gs": 420,
                            "track": 90,
                            "seen": 3,
                            "flight": "LOT285",
                        },
                        {
                            "hex": "outside",
                            "lat": 60.0,
                            "lon": 10.0,
                            "alt_baro": 18000,
                            "gs": 380,
                            "track": 80,
                            "seen": 2,
                        },
                    ],
                },
                {
                    "now": 1_002,
                    "ac": [
                        {
                            "hex": "abc123",
                            "lat": 52.21,
                            "lon": 21.01,
                            "alt_baro": 21000,
                            "gs": 430,
                            "track": 92,
                            "seen": 1,
                            "flight": "LOT285",
                            "r": "SP-LVQ",
                        },
                        {
                            "hex": "def456",
                            "lat": 52.4,
                            "lon": 21.4,
                            "alt_baro": 32000,
                            "gs": 470,
                            "track": 120,
                            "seen": 4,
                            "flight": "RYR7AB",
                        },
                    ],
                },
            ]
        )

        payload = client.fetch_flights(
            {
                "lamin": 51.0,
                "lamax": 54.0,
                "lomin": 19.0,
                "lomax": 23.0,
            }
        )

        self.assertEqual(len(client.requests), 2)
        self.assertEqual(payload["count"], 2)
        self.assertEqual({flight["icao24"] for flight in payload["flights"]}, {"abc123", "def456"})
        merged = next(flight for flight in payload["flights"] if flight["icao24"] == "abc123")
        self.assertEqual(merged["registration"], "SP-LVQ")


if __name__ == "__main__":
    unittest.main()
