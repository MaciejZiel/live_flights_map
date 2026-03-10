from __future__ import annotations

from math import cos, radians

from .provider_base import FlightProviderError


class AirportWorkflowService:
    def __init__(
        self,
        airport_catalog_service,
        traffic_intelligence_service,
        snapshot_service,
    ) -> None:
        self.airport_catalog_service = airport_catalog_service
        self.traffic_intelligence_service = traffic_intelligence_service
        self.snapshot_service = snapshot_service

    def list_airports(self, bbox: dict[str, float], limit: int) -> dict[str, object]:
        catalog_airports = self.airport_catalog_service.list_airports_in_bbox(
            bbox=bbox,
            limit=max(limit, 1),
        )
        known_airports = self.traffic_intelligence_service.list_known_airports_in_bbox(
            bbox=bbox,
            limit=max(limit * 2, limit),
        )

        merged = {}
        for airport in catalog_airports + known_airports:
            key = airport.get("entity_key") or airport.get("iata") or airport.get("icao")
            if not key:
                continue
            merged[key] = {
                **airport,
                "entity_type": "airport",
            }

        airports = list(merged.values())[: max(limit, 1)]
        return {
            "count": len(airports),
            "airports": airports,
        }

    def get_airport_dashboard(
        self,
        airport_code: str,
        hours: int,
        limit: int,
    ) -> dict[str, object] | None:
        airport = self.airport_catalog_service.get_airport(airport_code)
        if airport is None:
            airport = self.traffic_intelligence_service.get_known_airport(airport_code)
        if airport is None:
            return None

        bbox = self._build_local_bbox(airport["latitude"], airport["longitude"], radius_km=55)
        try:
            snapshot = self.snapshot_service.get_flights(bbox=bbox)
            snapshot_warning = None
        except FlightProviderError as exc:
            snapshot = {"flights": [], "count": 0, "meta": {"source": "archive"}}
            snapshot_warning = str(exc)
        movements = self.traffic_intelligence_service.list_airport_movements(
            airport_codes=[
                airport.get("icao"),
                airport.get("iata"),
                airport.get("entity_key"),
            ],
            hours=hours,
            limit=limit,
        )

        nearby_live = []
        on_ground = []
        live_arrivals = []
        live_departures = []

        for flight in snapshot.get("flights", []):
            distance_km = self._distance_km(
                airport["latitude"],
                airport["longitude"],
                flight.get("latitude"),
                flight.get("longitude"),
            )
            if distance_km > 65:
                continue
            flight_payload = {
                "icao24": flight.get("icao24"),
                "callsign": flight.get("callsign"),
                "registration": flight.get("registration"),
                "type_code": flight.get("type_code"),
                "origin_country": flight.get("origin_country"),
                "latitude": flight.get("latitude"),
                "longitude": flight.get("longitude"),
                "altitude": flight.get("altitude"),
                "velocity": flight.get("velocity"),
                "true_track": flight.get("true_track"),
                "on_ground": bool(flight.get("on_ground")),
                "distance_km": round(distance_km, 1),
            }
            nearby_live.append(flight_payload)
            if flight_payload["on_ground"] or distance_km < 4.5:
                on_ground.append(flight_payload)

        airport_codes = {
            str(code).strip().upper()
            for code in (
                airport.get("icao"),
                airport.get("iata"),
                airport.get("entity_key"),
            )
            if code
        }
        for item in movements["arrivals"]:
            if item.get("destination", "").upper() in airport_codes:
                live_arrivals.append(item)
        for item in movements["departures"]:
            if item.get("origin", "").upper() in airport_codes:
                live_departures.append(item)

        timeline = self._build_timeline(movements["arrivals"], movements["departures"], hours)

        return {
            "airport": airport,
            "live": {
                "count": len(nearby_live),
                "nearby": nearby_live[: max(limit * 2, limit)],
                "on_ground": on_ground[: max(limit, 1)],
                "arrivals": live_arrivals[: max(limit, 1)],
                "departures": live_departures[: max(limit, 1)],
            },
            "recent": {
                "arrivals": movements["arrivals"][: max(limit, 1)],
                "departures": movements["departures"][: max(limit, 1)],
            },
            "stats": {
                "arrivals": len(movements["arrivals"]),
                "departures": len(movements["departures"]),
                "ground": len(on_ground),
                "nearby": len(nearby_live),
            },
            "history": timeline,
            "meta": {
                "warning": snapshot_warning,
                "source": snapshot.get("meta", {}).get("source", "archive"),
            },
        }

    @staticmethod
    def _build_local_bbox(latitude: float, longitude: float, radius_km: float) -> dict[str, float]:
        radius_lat = radius_km / 111.0
        radius_lon = radius_km / max(30.0, 111.0 * cos(radians(latitude)))
        return {
            "lamin": latitude - radius_lat,
            "lamax": latitude + radius_lat,
            "lomin": longitude - radius_lon,
            "lomax": longitude + radius_lon,
        }

    @staticmethod
    def _distance_km(
        start_latitude: float,
        start_longitude: float,
        end_latitude: float | None,
        end_longitude: float | None,
    ) -> float:
        if end_latitude is None or end_longitude is None:
            return 999999.0
        delta_lat = (float(end_latitude) - float(start_latitude)) * 111.0
        delta_lon = (float(end_longitude) - float(start_longitude)) * 111.0 * max(
            0.35,
            cos(radians(start_latitude)),
        )
        return (delta_lat ** 2 + delta_lon ** 2) ** 0.5

    @staticmethod
    def _build_timeline(
        arrivals: list[dict[str, object]],
        departures: list[dict[str, object]],
        hours: int,
    ) -> list[dict[str, object]]:
        buckets = {}
        for item in arrivals:
            hour_key = str(item.get("fetched_at", ""))[:13]
            buckets.setdefault(hour_key, {"arrivals": 0, "departures": 0})
            buckets[hour_key]["arrivals"] += 1
        for item in departures:
            hour_key = str(item.get("fetched_at", ""))[:13]
            buckets.setdefault(hour_key, {"arrivals": 0, "departures": 0})
            buckets[hour_key]["departures"] += 1

        timeline = []
        for key in sorted(buckets.keys())[-max(hours, 1) :]:
            timeline.append(
                {
                    "hour": key,
                    "arrivals": buckets[key]["arrivals"],
                    "departures": buckets[key]["departures"],
                }
            )
        return timeline
