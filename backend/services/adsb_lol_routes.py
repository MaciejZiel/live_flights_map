from __future__ import annotations

from typing import Any

import requests

from .provider_base import FlightProviderError, FlightProviderRateLimitError


class ADSBLolRouteError(FlightProviderError):
    pass


class ADSBLolRouteRateLimitError(FlightProviderRateLimitError, ADSBLolRouteError):
    pass


class ADSBLolRouteClient:
    name = "adsb_lol_routes"

    def __init__(self, base_url: str, timeout: float, max_retries: int) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max(max_retries, 0)
        self.session = requests.Session()

    def lookup_route(
        self,
        callsign: str,
        latitude: float | None,
        longitude: float | None,
    ) -> dict[str, Any] | None:
        normalized_callsign = callsign.strip().upper()
        if not normalized_callsign or latitude is None or longitude is None:
            return None

        response = self._request_route_lookup(
            {
                "planes": [
                    {
                        "callsign": normalized_callsign,
                        "lat": latitude,
                        "lng": longitude,
                    }
                ]
            }
        )
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            return None

        route = payload[0]
        if not isinstance(route, dict):
            return None

        airports = route.get("_airports") or []
        normalized_airports = [
            self._normalize_airport(airport)
            for airport in airports
            if isinstance(airport, dict)
        ]
        normalized_airports = [airport for airport in normalized_airports if airport]
        if not normalized_airports:
            return None

        route_label = " -> ".join(
            airport.get("iata") or airport.get("icao") or airport.get("location") or "?"
            for airport in normalized_airports
        )
        route_verbose = " -> ".join(
            airport.get("location") or airport.get("name") or airport.get("iata") or "Unknown"
            for airport in normalized_airports
        )

        return {
            "callsign": route.get("callsign") or normalized_callsign,
            "airline_code": self._normalize_text(route.get("airline_code"), uppercase=True),
            "airline_name": self._normalize_text(
                route.get("airline_name") or route.get("airline")
            ),
            "flight_number": self._normalize_text(route.get("number"), uppercase=True),
            "airport_codes": self._normalize_text(route.get("airport_codes"), uppercase=True),
            "iata_codes": self._normalize_text(route.get("_airport_codes_iata"), uppercase=True),
            "origin": normalized_airports[0],
            "destination": normalized_airports[-1],
            "stops": normalized_airports[1:-1],
            "airports": normalized_airports,
            "plausible": bool(route.get("plausible", True)),
            "route_label": route_label,
            "route_verbose": route_verbose,
        }

    def _request_route_lookup(self, payload: dict[str, object]) -> requests.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    self.base_url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response
            except requests.Timeout as exc:
                if attempt < self.max_retries:
                    continue
                raise ADSBLolRouteError("ADSB.lol route lookup timed out.") from exc
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code == 429:
                    raise ADSBLolRouteRateLimitError("ADSB.lol route lookup rate limited.") from exc
                raise ADSBLolRouteError(
                    f"ADSB.lol route lookup returned HTTP {status_code}."
                ) from exc
            except requests.ConnectionError as exc:
                if attempt < self.max_retries:
                    continue
                raise ADSBLolRouteError(
                    "Could not reach ADSB.lol route lookup from the current environment."
                ) from exc
            except requests.RequestException as exc:
                raise ADSBLolRouteError("Unable to fetch route data from ADSB.lol.") from exc

        raise ADSBLolRouteError("Unable to fetch route data from ADSB.lol.")

    @staticmethod
    def _normalize_airport(airport: dict[str, Any]) -> dict[str, Any] | None:
        icao = ADSBLolRouteClient._normalize_text(airport.get("icao"), uppercase=True)
        iata = ADSBLolRouteClient._normalize_text(airport.get("iata"), uppercase=True)
        name = ADSBLolRouteClient._normalize_text(airport.get("name"))
        location = ADSBLolRouteClient._normalize_text(airport.get("location"))
        if not any((icao, iata, name, location)):
            return None

        return {
            "icao": icao,
            "iata": iata,
            "name": name,
            "location": location,
            "country_iso2": ADSBLolRouteClient._normalize_text(
                airport.get("countryiso2"),
                uppercase=True,
            ),
            "latitude": ADSBLolRouteClient._normalize_float(airport.get("lat")),
            "longitude": ADSBLolRouteClient._normalize_float(airport.get("lon")),
        }

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned

    @staticmethod
    def _normalize_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
