from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

from .provider_base import FlightProviderError


@dataclass(slots=True)
class DetailCacheEntry:
    payload: dict[str, object]
    expires_at: float


class FlightDetailsService:
    def __init__(
        self,
        route_client,
        photo_client,
        cache_ttl: float,
    ) -> None:
        self.route_client = route_client
        self.photo_client = photo_client
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple[str, str | None, str | None], DetailCacheEntry] = {}
        self._lock = Lock()

    def get_details(
        self,
        icao24: str,
        callsign: str | None = None,
        registration: str | None = None,
        type_code: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        origin_country: str | None = None,
    ) -> dict[str, object]:
        normalized_icao24 = str(icao24).strip().lower()
        normalized_callsign = self._normalize_text(callsign, uppercase=True)
        normalized_registration = self._normalize_text(registration, uppercase=True)
        normalized_type_code = self._normalize_text(type_code, uppercase=True)
        cache_key = (normalized_icao24, normalized_callsign, normalized_registration)
        now = monotonic()

        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and cached.expires_at > now:
                return deepcopy(cached.payload)

        warnings = []

        try:
            route = self.route_client.lookup_route(
                callsign=normalized_callsign or "",
                latitude=latitude,
                longitude=longitude,
            )
        except FlightProviderError as exc:
            route = None
            warnings.append(str(exc))

        try:
            photo = self.photo_client.fetch_photo(normalized_registration)
        except FlightProviderError as exc:
            photo = None
            warnings.append(str(exc))

        payload = {
            "aircraft": {
                "icao24": normalized_icao24,
                "callsign": normalized_callsign,
                "registration": normalized_registration,
                "type_code": normalized_type_code,
                "origin_country": self._normalize_text(origin_country),
                "operator_code": self._derive_operator_code(normalized_callsign),
            },
            "route": route,
            "photo": photo,
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "warning": " ".join(warnings) if warnings else None,
            },
        }

        with self._lock:
            self._cache[cache_key] = DetailCacheEntry(
                payload=payload,
                expires_at=monotonic() + self.cache_ttl,
            )

        return deepcopy(payload)

    @staticmethod
    def _derive_operator_code(callsign: str | None) -> str | None:
        if not callsign:
            return None
        if len(callsign) < 3 or not callsign[:3].isalpha():
            return None
        return callsign[:3]

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned
