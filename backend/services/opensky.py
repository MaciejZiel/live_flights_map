from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import requests

from .provider_base import (
    FlightProviderError,
    FlightProviderRateLimitError,
    parse_retry_after_seconds,
)


class OpenSkyError(FlightProviderError):
    pass


class OpenSkyRateLimitError(FlightProviderRateLimitError, OpenSkyError):
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
    name = "opensky"

    def __init__(
        self,
        base_url: str,
        username: str | None,
        password: str | None,
        timeout: float,
        max_retries: int,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_url: str = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max(max_retries, 0)
        self.client_id = client_id.strip() if client_id else None
        self.client_secret = client_secret.strip() if client_secret else None
        self.token_url = token_url
        self.session = requests.Session()
        if not (self.client_id and self.client_secret) and username and password:
            self.session.auth = (username, password)
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0
        self._token_lock = Lock()
        self.last_rate_limit_remaining: int | None = None
        self.last_rate_limit_reset: int | None = None

    def fetch_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        response = self._request_snapshot(bbox)
        self.last_rate_limit_remaining = self._parse_header_int(
            response.headers.get("X-Rate-Limit-Remaining")
        )
        self.last_rate_limit_reset = self._parse_header_int(
            response.headers.get("X-Rate-Limit-Reset")
        )

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
        token_retry_available = bool(self.client_id and self.client_secret)
        while True:
            unauthorized = False
            for attempt in range(self.max_retries + 1):
                try:
                    headers = self._authorization_headers()
                    response = self.session.get(
                        self.base_url,
                        params=bbox,
                        headers=headers or None,
                        timeout=self.timeout,
                    )
                    if response.status_code == 401 and token_retry_available:
                        self._invalidate_access_token()
                        token_retry_available = False
                        unauthorized = True
                        break
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
                        headers = exc.response.headers if exc.response is not None else {}
                        raise OpenSkyRateLimitError(
                            "OpenSky rate limit exceeded.",
                            retry_after_seconds=parse_retry_after_seconds(headers),
                        ) from exc
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

            if unauthorized:
                continue
            break

        raise OpenSkyError("OpenSky rejected the OAuth credentials.")

    def _authorization_headers(self) -> dict[str, str]:
        if not (self.client_id and self.client_secret):
            return {}

        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    def _get_access_token(self) -> str:
        with self._token_lock:
            if self._access_token and monotonic() < self._access_token_expires_at:
                return self._access_token

            try:
                response = self.session.post(
                    self.token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                token = payload.get("access_token")
                if not isinstance(token, str) or not token.strip():
                    raise OpenSkyError("OpenSky returned an invalid OAuth token response.")
                expires_in = max(float(payload.get("expires_in", 1800)), 1.0)
            except OpenSkyError:
                raise
            except (requests.RequestException, TypeError, ValueError) as exc:
                raise OpenSkyError("Could not authenticate with OpenSky OAuth2.") from exc

            self._access_token = token.strip()
            self._access_token_expires_at = monotonic() + max(expires_in - 60, 1.0)
            return self._access_token

    def _invalidate_access_token(self) -> None:
        with self._token_lock:
            self._access_token = None
            self._access_token_expires_at = 0.0

    @staticmethod
    def _parse_header_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

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
