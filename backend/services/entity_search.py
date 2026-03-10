from __future__ import annotations


class EntitySearchService:
    def __init__(
        self,
        archive_service,
        airport_catalog_service,
        traffic_intelligence_service,
        lookback_hours: float,
    ) -> None:
        self.archive_service = archive_service
        self.airport_catalog_service = airport_catalog_service
        self.traffic_intelligence_service = traffic_intelligence_service
        self.lookback_hours = lookback_hours

    def search(self, query: str, limit: int) -> dict[str, object]:
        normalized_limit = min(max(limit, 1), 12)
        flights_payload = self.archive_service.search_recent_flights(
            query=query,
            limit=normalized_limit,
            lookback_hours=self.lookback_hours,
        )
        flights = [
            {
                "entity_type": "flight",
                "entity_key": item["icao24"],
                "label": item["callsign"]
                or item["registration"]
                or item["icao24"].upper(),
                "subtitle": " · ".join(
                    part
                    for part in (
                        item.get("registration") or item["icao24"].upper(),
                        item.get("type_code"),
                        item.get("origin_country"),
                    )
                    if part
                ),
                **item,
            }
            for item in flights_payload["results"]
        ]
        airports = self.airport_catalog_service.search_airports(query, normalized_limit)
        known_airports = self.traffic_intelligence_service.list_known_airports_in_bbox(
            bbox={"lamin": -90.0, "lamax": 90.0, "lomin": -180.0, "lomax": 180.0},
            limit=normalized_limit * 4,
        )
        normalized_query = query.strip().lower()
        for known_airport in known_airports:
            if normalized_query in " ".join(
                part.lower()
                for part in (
                    known_airport.get("entity_key", ""),
                    known_airport.get("icao", "") or "",
                    known_airport.get("iata", "") or "",
                    known_airport.get("name", "") or "",
                    known_airport.get("city", "") or "",
                    known_airport.get("country", "") or "",
                )
                if part
            ):
                airports.append(known_airport)

        airport_results = []
        seen_airports = set()
        for airport in airports:
            airport_key = airport.get("entity_key") or airport.get("icao") or airport.get("iata")
            if not airport_key or airport_key in seen_airports:
                continue
            seen_airports.add(airport_key)
            airport_results.append(airport)
            if len(airport_results) >= normalized_limit:
                break

        airlines = self.traffic_intelligence_service.search_airlines(
            query=query,
            limit=normalized_limit,
            lookback_hours=self.lookback_hours,
        )
        routes = self.traffic_intelligence_service.search_routes(
            query=query,
            limit=normalized_limit,
        )
        locations = self.airport_catalog_service.search_locations(
            query=query,
            limit=max(4, normalized_limit // 2),
        )

        ordered_groups = [
            ("flights", flights),
            ("airports", airport_results),
            ("airlines", airlines),
            ("routes", routes),
            ("locations", locations),
        ]
        results = []
        for _, group in ordered_groups:
            results.extend(group)

        return {
            "query": query.strip(),
            "count": len(results),
            "results": results[: normalized_limit * 4],
            "groups": {
                name: group
                for name, group in ordered_groups
                if group
            },
        }
