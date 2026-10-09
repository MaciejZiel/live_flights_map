from __future__ import annotations

import unittest

from backend.demo import WORLD_BBOX
from backend.services.demo_traffic import (
    AIRPORTS,
    SyntheticRouteClient,
    SyntheticTrafficProvider,
    build_fleet,
    flight_leg_at,
    flight_state_at,
    great_circle_km,
    interpolate_great_circle,
)

EUROPE_BBOX = {"lamin": 34.0, "lamax": 72.0, "lomin": -25.0, "lomax": 45.0}


class SyntheticTrafficTests(unittest.TestCase):
    def test_fleet_is_deterministic_and_clearly_synthetic(self) -> None:
        first = build_fleet(200, seed=7)
        second = build_fleet(200, seed=7)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 200)
        self.assertEqual(len({flight.icao24 for flight in first}), 200)
        self.assertTrue(all(flight.callsign.startswith("DEMO") for flight in first))
        self.assertTrue(all(flight.registration.startswith("SYN-") for flight in first))
        self.assertNotEqual(first, build_fleet(200, seed=8))

    def test_great_circle_interpolation_hits_both_endpoints(self) -> None:
        waw, lhr = AIRPORTS[0], next(a for a in AIRPORTS if a["iata"] == "LHR")

        start = interpolate_great_circle(waw, lhr, 0.0)
        end = interpolate_great_circle(waw, lhr, 1.0)

        self.assertAlmostEqual(start[0], waw["latitude"], places=4)
        self.assertAlmostEqual(start[1], waw["longitude"], places=4)
        self.assertAlmostEqual(end[0], lhr["latitude"], places=4)
        self.assertAlmostEqual(end[1], lhr["longitude"], places=4)
        self.assertAlmostEqual(great_circle_km(waw, lhr), 1465, delta=25)

    def test_aircraft_move_between_snapshots_and_rest_on_the_ground(self) -> None:
        flight = build_fleet(1, seed=3)[0]
        base = flight.cycle_seconds * 10_000 - flight.phase_offset_seconds  # start of the outbound leg

        departing = flight_state_at(flight, base + 60)
        cruising = flight_state_at(flight, base + flight.leg_seconds / 2)
        later = flight_state_at(flight, base + flight.leg_seconds / 2 + 60)
        parked = flight_state_at(flight, base + flight.leg_seconds + 60)

        self.assertFalse(cruising["on_ground"])
        self.assertGreater(departing["vertical_rate"], 0)
        self.assertLess(departing["altitude"], cruising["altitude"])
        self.assertEqual(cruising["altitude"], flight.cruise_altitude_m)
        self.assertNotEqual((cruising["latitude"], cruising["longitude"]), (later["latitude"], later["longitude"]))
        self.assertTrue(parked["on_ground"])
        self.assertEqual(parked["latitude"], round(flight.destination["latitude"], 5))
        self.assertIsNone(flight_leg_at(flight, base + flight.leg_seconds + 60)[2])

    def test_snapshot_respects_the_bounding_box(self) -> None:
        provider = SyntheticTrafficProvider(flight_count=300, seed=11, clock=lambda: 1_800_000_000)

        world = provider.fetch_flights(WORLD_BBOX)
        europe = provider.fetch_flights(EUROPE_BBOX)

        self.assertEqual(world["count"], 300)
        self.assertGreater(europe["count"], 100)
        self.assertLess(europe["count"], world["count"])
        for flight in europe["flights"]:
            self.assertTrue(EUROPE_BBOX["lamin"] <= flight["latitude"] <= EUROPE_BBOX["lamax"])
            self.assertTrue(flight["synthetic"])
            self.assertEqual(flight["origin_country"], "Synthetic")

    def test_route_client_describes_the_current_leg(self) -> None:
        provider = SyntheticTrafficProvider(flight_count=20, seed=5, clock=lambda: 1_800_000_000)
        flight = provider.fleet[0]

        route = SyntheticRouteClient(provider).lookup_route(flight.callsign.lower())

        self.assertEqual(route["airline_name"], "Synthetic Demo Air")
        self.assertEqual({route["origin"]["iata"], route["destination"]["iata"]}, {flight.origin["iata"], flight.destination["iata"]})
        self.assertIsNone(SyntheticRouteClient(provider).lookup_route("LOT123"))


if __name__ == "__main__":
    unittest.main()
