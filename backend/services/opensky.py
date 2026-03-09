from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests


class OpenSkyError(Exception):
    pass


@dataclass(slots=True)
class FlightState:
    icao24: str
    callsign: str | None
    longitude: float
    latitude: float
    true_track: float | None
    altitude: float | None


class OpenSkyClient:
    def __init__(
        self,
        base_url: str,
        username: str | None,
        password: str | None,
        timeout: float,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)

    def fetch_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        try:
            response = self.session.get(
                self.base_url,
                params=bbox,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OpenSkyError("Unable to fetch data from OpenSky.") from exc

        payload = response.json()
        states = payload.get("states") or []
        flights = [asdict(flight) for flight in self._normalize_states(states)]
        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bbox": bbox,
            "count": len(flights),
            "flights": flights,
        }

    def _normalize_states(self, states: list[list[object]]) -> list[FlightState]:
        normalized: list[FlightState] = []

        for state in states:
            if len(state) < 14:
                continue

            icao24 = self._as_str(state[0])
            longitude = self._as_float(state[5])
            latitude = self._as_float(state[6])
            altitude = self._as_float(state[13])
            true_track = self._as_float(state[10])

            if not icao24 or longitude is None or latitude is None:
                continue

            normalized.append(
                FlightState(
                    icao24=icao24,
                    callsign=self._clean_callsign(state[1]),
                    longitude=longitude,
                    latitude=latitude,
                    true_track=true_track,
                    altitude=altitude,
                )
            )

        return normalized

    @staticmethod
    def _clean_callsign(value: object) -> str | None:
        if value is None:
            return None
        callsign = str(value).strip()
        return callsign or None

    @staticmethod
    def _as_str(value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None

    @staticmethod
    def _as_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
