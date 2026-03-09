from __future__ import annotations

import math
from datetime import datetime, timezone

import requests

from .provider_base import FlightProviderError, FlightProviderRateLimitError

KNOTS_TO_METERS_PER_SECOND = 0.514444
FEET_TO_METERS = 0.3048
FEET_PER_MINUTE_TO_METERS_PER_SECOND = 0.00508
EARTH_RADIUS_KM = 6371.0


class ADSBLolError(FlightProviderError):
    pass


class ADSBLolRateLimitError(FlightProviderRateLimitError, ADSBLolError):
    pass


class ADSBLolClient:
    name = "adsb_lol"

    def __init__(
        self,
        base_url: str,
        timeout: float,
        max_retries: int,
        radius_limit_nm: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(max_retries, 0)
        self.radius_limit_nm = max(radius_limit_nm, 1)
        self.session = requests.Session()

    def fetch_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        center_latitude, center_longitude, radius_nm = self._build_search_area(bbox)
        response = self._request_snapshot(center_latitude, center_longitude, radius_nm)
        payload = response.json()
        now_timestamp = self._as_float(payload.get("now"))
        aircraft = payload.get("ac") or []

        flights = []
        for aircraft_state in aircraft:
            normalized = self._normalize_aircraft(aircraft_state, now_timestamp)
            if not normalized:
                continue

            if not self._is_within_bbox(
                normalized["latitude"],
                normalized["longitude"],
                bbox,
            ):
                continue

            flights.append(normalized)

        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bbox": bbox,
            "count": len(flights),
            "flights": flights,
        }

    def _request_snapshot(
        self,
        latitude: float,
        longitude: float,
        radius_nm: int,
    ) -> requests.Response:
        endpoint = f"{self.base_url}/v2/point/{latitude:.5f}/{longitude:.5f}/{radius_nm}"

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(endpoint, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.Timeout as exc:
                if attempt < self.max_retries:
                    continue
                raise ADSBLolError("ADSB.lol request timed out.") from exc
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code == 429:
                    raise ADSBLolRateLimitError("ADSB.lol rate limit exceeded.") from exc
                raise ADSBLolError(f"ADSB.lol returned HTTP {status_code}.") from exc
            except requests.ConnectionError as exc:
                if attempt < self.max_retries:
                    continue
                raise ADSBLolError("Could not reach ADSB.lol from the current environment.") from exc
            except requests.RequestException as exc:
                raise ADSBLolError("Unable to fetch data from ADSB.lol.") from exc

        raise ADSBLolError("Unable to fetch data from ADSB.lol.")

    def _build_search_area(self, bbox: dict[str, float]) -> tuple[float, float, int]:
        center_latitude = (bbox["lamin"] + bbox["lamax"]) / 2
        center_longitude = (bbox["lomin"] + bbox["lomax"]) / 2
        corners = (
            (bbox["lamin"], bbox["lomin"]),
            (bbox["lamin"], bbox["lomax"]),
            (bbox["lamax"], bbox["lomin"]),
            (bbox["lamax"], bbox["lomax"]),
        )
        radius_km = max(
            self._haversine_km(center_latitude, center_longitude, corner_latitude, corner_longitude)
            for corner_latitude, corner_longitude in corners
        )
        radius_nm = math.ceil(radius_km / 1.852)
        radius_nm = max(1, min(radius_nm, self.radius_limit_nm))
        return center_latitude, center_longitude, radius_nm

    def _normalize_aircraft(
        self,
        aircraft: dict[str, object],
        now_timestamp: float | None,
    ) -> dict[str, object] | None:
        icao24 = self._as_str(aircraft.get("hex"))
        latitude = self._as_float(aircraft.get("lat"))
        longitude = self._as_float(aircraft.get("lon"))
        if not icao24 or latitude is None or longitude is None:
            return None

        altitude_feet = self._as_float(aircraft.get("alt_baro"))
        on_ground = aircraft.get("alt_baro") == "ground"
        vertical_rate = self._as_float(aircraft.get("baro_rate"))
        velocity_knots = self._as_float(aircraft.get("gs"))
        seen_seconds = self._as_float(aircraft.get("seen_pos")) or self._as_float(aircraft.get("seen"))
        last_contact = None
        if now_timestamp is not None and seen_seconds is not None:
            last_contact = max(0, int(now_timestamp - seen_seconds))

        return {
            "icao24": icao24,
            "callsign": self._clean_callsign(aircraft.get("flight")),
            "origin_country": None,
            "longitude": longitude,
            "latitude": latitude,
            "last_contact": last_contact,
            "true_track": self._as_float(aircraft.get("track")),
            "altitude": None if altitude_feet is None else altitude_feet * FEET_TO_METERS,
            "velocity": None if velocity_knots is None else velocity_knots * KNOTS_TO_METERS_PER_SECOND,
            "vertical_rate": None if vertical_rate is None else vertical_rate * FEET_PER_MINUTE_TO_METERS_PER_SECOND,
            "on_ground": on_ground,
        }

    @staticmethod
    def _is_within_bbox(latitude: float, longitude: float, bbox: dict[str, float]) -> bool:
        return (
            bbox["lamin"] <= latitude <= bbox["lamax"]
            and bbox["lomin"] <= longitude <= bbox["lomax"]
        )

    @staticmethod
    def _haversine_km(
        left_latitude: float,
        left_longitude: float,
        right_latitude: float,
        right_longitude: float,
    ) -> float:
        left_latitude_radians = math.radians(left_latitude)
        right_latitude_radians = math.radians(right_latitude)
        delta_latitude = math.radians(right_latitude - left_latitude)
        delta_longitude = math.radians(right_longitude - left_longitude)
        haversine = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(left_latitude_radians)
            * math.cos(right_latitude_radians)
            * math.sin(delta_longitude / 2) ** 2
        )
        return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))

    @staticmethod
    def _clean_callsign(value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _as_str(value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None

    @staticmethod
    def _as_float(value: object) -> float | None:
        if value is None or value == "ground":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
