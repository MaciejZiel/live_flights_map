from __future__ import annotations

import unittest

from backend.services.flight_details import FlightDetailsService


class _RouteClientStub:
    def __init__(self, route: dict[str, object] | None = None) -> None:
        self.route = route
        self.calls = 0

    def lookup_route(
        self,
        *,
        callsign: str,
        latitude: float | None,
        longitude: float | None,
    ) -> dict[str, object] | None:
        self.calls += 1
        return self.route


class _PhotoClientStub:
    def __init__(self, responses: list[dict[str, object] | None]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def fetch_photo(
        self,
        registration: str | None,
        *,
        type_code: str | None = None,
        operator_code: str | None = None,
        airline_code: str | None = None,
        airline_name: str | None = None,
    ) -> dict[str, object] | None:
        self.calls += 1
        if self.responses:
            return self.responses.pop(0)
        return None


class FlightDetailsServiceTests(unittest.TestCase):
    def test_reuses_cached_payload_when_photo_is_already_present(self) -> None:
        route_client = _RouteClientStub()
        photo_client = _PhotoClientStub(
            [
                {
                    "thumbnail_url": "https://example.com/photo.jpg",
                    "source": "test",
                }
            ]
        )
        service = FlightDetailsService(
            route_client=route_client,
            photo_client=photo_client,
            cache_ttl=3600,
        )

        payload_a = service.get_details(
            icao24="48af06",
            callsign="LOT123",
            registration="SP-LVG",
            type_code="B38M",
        )
        payload_b = service.get_details(
            icao24="48af06",
            callsign="LOT123",
            registration="SP-LVG",
            type_code="B38M",
        )

        self.assertEqual(photo_client.calls, 1)
        self.assertEqual(route_client.calls, 1)
        self.assertEqual(
            payload_a["photo"]["thumbnail_url"],
            payload_b["photo"]["thumbnail_url"],
        )

    def test_retries_photo_lookup_when_cached_payload_has_no_photo(self) -> None:
        route_client = _RouteClientStub()
        photo_client = _PhotoClientStub(
            [
                None,
                {
                    "thumbnail_url": "https://example.com/recovered-photo.jpg",
                    "source": "test",
                },
            ]
        )
        service = FlightDetailsService(
            route_client=route_client,
            photo_client=photo_client,
            cache_ttl=3600,
        )

        payload_a = service.get_details(
            icao24="48af06",
            callsign="LOT123",
            registration="SP-LVG",
            type_code="B38M",
        )
        payload_b = service.get_details(
            icao24="48af06",
            callsign="LOT123",
            registration="SP-LVG",
            type_code="B38M",
        )

        self.assertIsNone(payload_a["photo"])
        self.assertEqual(photo_client.calls, 2)
        self.assertEqual(route_client.calls, 2)
        self.assertEqual(
            payload_b["photo"]["thumbnail_url"],
            "https://example.com/recovered-photo.jpg",
        )
        self.assertEqual(payload_b["meta"]["detail_quality"]["photo_state"], "exact")

    def test_marks_representative_photo_and_resolved_route_in_detail_quality(self) -> None:
        route_client = _RouteClientStub(
            {
                "airline_code": "LOT",
                "flight_number": "123",
                "plausible": True,
                "origin": {"iata": "WAW"},
                "destination": {"iata": "MAD"},
            }
        )
        photo_client = _PhotoClientStub(
            [
                {
                    "thumbnail_url": "https://example.com/representative-photo.jpg",
                    "source": "Wikimedia Commons",
                    "match_type": "representative",
                }
            ]
        )
        service = FlightDetailsService(
            route_client=route_client,
            photo_client=photo_client,
            cache_ttl=3600,
        )

        payload = service.get_details(
            icao24="48af06",
            callsign="LOT123",
            registration="SP-LVG",
            type_code="B38M",
            origin_country="Poland",
        )

        self.assertEqual(payload["meta"]["detail_quality"]["route_state"], "resolved")
        self.assertEqual(payload["meta"]["detail_quality"]["photo_state"], "representative")
        self.assertEqual(payload["meta"]["detail_quality"]["photo_source"], "Wikimedia Commons")
        self.assertIn("representative aircraft photo", payload["meta"]["detail_quality"]["summary"].lower())


if __name__ == "__main__":
    unittest.main()
