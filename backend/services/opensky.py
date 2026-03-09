from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests


class OpenSkyError(Exception):
    pass


class OpenSkyRateLimitError(OpenSkyError):
    pass


@dataclass(slots=True)
class FlightState:
    icao24: str
    callsign: str | None
    origin_country: str | None
    longitude: float
    latitude: float
    last_contact: int | None
    true_track: float | None
    altitude: float | None
    velocity: float | None
    vertical_rate: float | None
    on_ground: bool


class OpenSkyClient:
    def __init__(
        self,
        base_url: str,
        username: str | None,
        password: str | None,
        timeout: float,
        max_retries: int,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max(max_retries, 0)
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)

    def fetch_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        response = self._request_snapshot(bbox)

        payload = response.json()
        states = payload.get("states") or []
        flights = [asdict(flight) for flight in self._normalize_states(states)]
        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bbox": bbox,
            "count": len(flights),
            "flights": flights,
        }

    def _request_snapshot(self, bbox: dict[str, float]) -> requests.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    self.base_url,
                    params=bbox,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response
            except requests.Timeout as exc:
                if attempt < self.max_retries:
                    continue
                raise OpenSkyError("OpenSky request timed out.") from exc
            except requests.HTTPError as exc:
                status_code = (
                    exc.response.status_code if exc.response is not None else None
                )
                if status_code == 401:
                    message = "OpenSky rejected the credentials."
                elif status_code == 403:
                    message = "OpenSky denied access for this request."
                elif status_code == 429:
                    raise OpenSkyRateLimitError("OpenSky rate limit exceeded.") from exc
                else:
                    message = f"OpenSky returned HTTP {status_code}."
                raise OpenSkyError(message) from exc
            except requests.ConnectionError as exc:
                if attempt < self.max_retries:
                    continue
                raise OpenSkyError(
                    "Could not reach OpenSky from the current environment."
                ) from exc
            except requests.RequestException as exc:
                raise OpenSkyError("Unable to fetch data from OpenSky.") from exc

        raise OpenSkyError("Unable to fetch data from OpenSky.")

    def _normalize_states(self, states: list[list[object]]) -> list[FlightState]:
        normalized: list[FlightState] = []

        for state in states:
            if len(state) < 14:
                continue

            icao24 = self._as_str(state[0])
            longitude = self._as_float(state[5])
            latitude = self._as_float(state[6])
            last_contact = self._as_int(state[4])
            altitude = self._as_float(state[7]) or self._as_float(state[13])
            velocity = self._as_float(state[9])
            true_track = self._as_float(state[10])
            vertical_rate = self._as_float(state[11])
            on_ground = self._as_bool(state[8], default=False)

            if not icao24 or longitude is None or latitude is None:
                continue

            normalized.append(
                FlightState(
                    icao24=icao24,
                    callsign=self._clean_callsign(state[1]),
                    origin_country=self._clean_callsign(state[2]),
                    longitude=longitude,
                    latitude=latitude,
                    last_contact=last_contact,
                    true_track=true_track,
                    altitude=altitude,
                    velocity=velocity,
                    vertical_rate=vertical_rate,
                    on_ground=on_ground,
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

    @staticmethod
    def _as_bool(value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        return default

    @staticmethod
    def _as_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
