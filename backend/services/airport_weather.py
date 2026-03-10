from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from time import monotonic

import requests


class AirportWeatherError(Exception):
    pass


@dataclass(slots=True)
class AirportWeatherCacheEntry:
    payload: dict[str, object]
    expires_at: float


class AirportWeatherService:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        cache_ttl: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = max(float(timeout), 1.0)
        self.cache_ttl = max(float(cache_ttl), 60.0)
        self.session = requests.Session()
        self._cache: dict[str, AirportWeatherCacheEntry] = {}
        self._lock = Lock()

    def get_weather(self, station_code: str) -> dict[str, object]:
        normalized_code = self._normalize_station_code(station_code)
        now = monotonic()

        with self._lock:
            cached = self._cache.get(normalized_code)
            if cached and cached.expires_at > now:
                return deepcopy(cached.payload)

        payload = self._fetch_weather(normalized_code)

        with self._lock:
            self._cache[normalized_code] = AirportWeatherCacheEntry(
                payload=payload,
                expires_at=monotonic() + self.cache_ttl,
            )

        return deepcopy(payload)

    def _fetch_weather(self, station_code: str) -> dict[str, object]:
        try:
            response = self.session.get(
                self.base_url,
                params={
                    "ids": station_code,
                    "format": "json",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise AirportWeatherError("Airport weather request timed out.") from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            raise AirportWeatherError(
                f"Airport weather provider returned HTTP {status_code}."
            ) from exc
        except requests.ConnectionError as exc:
            raise AirportWeatherError(
                "Could not reach the airport weather provider from the current environment."
            ) from exc
        except requests.RequestException as exc:
            raise AirportWeatherError("Failed to load airport weather.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AirportWeatherError("Received an invalid airport weather response.") from exc

        if not isinstance(payload, list) or not payload:
            raise AirportWeatherError(
                "No current METAR is available for this airport."
            )

        station_payload = payload[0]
        if not isinstance(station_payload, dict):
            raise AirportWeatherError("Received an invalid airport weather payload.")

        return station_payload

    @staticmethod
    def _normalize_station_code(value: str) -> str:
        normalized = str(value or "").strip().upper()
        if not normalized:
            raise AirportWeatherError("Missing airport weather station.")
        return normalized
