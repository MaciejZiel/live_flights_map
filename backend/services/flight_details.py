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
            if cached and cached.expires_at > now and self._should_use_cached_entry(
                cached.payload,
                registration=normalized_registration,
                type_code=normalized_type_code,
                callsign=normalized_callsign,
            ):
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
            photo = self.photo_client.fetch_photo(
                normalized_registration,
                type_code=normalized_type_code,
                operator_code=self._derive_operator_code(normalized_callsign),
                airline_code=self._normalize_text(route.get("airline_code"), uppercase=True)
                if isinstance(route, dict)
                else None,
                airline_name=self._normalize_text(route.get("airline_name"))
                if isinstance(route, dict)
                else None,
            )
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
                "detail_quality": self._build_detail_quality(
                    route=route,
                    photo=photo,
                    callsign=normalized_callsign,
                    registration=normalized_registration,
                    type_code=normalized_type_code,
                    origin_country=self._normalize_text(origin_country),
                    operator_code=self._derive_operator_code(normalized_callsign),
                ),
            },
        }

        with self._lock:
            self._cache[cache_key] = DetailCacheEntry(
                payload=payload,
                expires_at=monotonic() + self.cache_ttl,
            )

        return deepcopy(payload)

    @staticmethod
    def _should_use_cached_entry(
        payload: dict[str, object],
        *,
        registration: str | None,
        type_code: str | None,
        callsign: str | None,
    ) -> bool:
        photo = payload.get("photo")
        if isinstance(photo, dict) and photo.get("thumbnail_url"):
            return True

        # Retry details that currently have enough identity context to potentially
        # resolve a photo, instead of pinning a stale "no photo" cache entry for hours.
        if registration or type_code or callsign:
            return False

        return True

    @staticmethod
    def _derive_operator_code(callsign: str | None) -> str | None:
        if not callsign:
            return None
        if len(callsign) < 3 or not callsign[:3].isalpha():
            return None
        return callsign[:3]

    @staticmethod
    def _build_detail_quality(
        *,
        route: dict[str, object] | None,
        photo: dict[str, object] | None,
        callsign: str | None,
        registration: str | None,
        type_code: str | None,
        origin_country: str | None,
        operator_code: str | None,
    ) -> dict[str, object]:
        route_state = (
            "unverified"
            if isinstance(route, dict) and route.get("plausible") is False
            else "resolved"
            if route
            else "pending"
        )
        photo_match_type = str(photo.get("match_type") or "").strip().lower() if isinstance(photo, dict) else ""
        photo_state = (
            "exact"
            if photo and photo_match_type != "representative"
            else "representative"
            if photo
            else "missing"
        )
        identity_fields = [
            bool(callsign),
            bool(registration),
            bool(type_code),
            bool(origin_country),
            bool(operator_code),
        ]
        identity_score = round((sum(identity_fields) / len(identity_fields)) * 100)
        quality_score = min(
            100,
            round(
                identity_score * 0.4
                + (30 if route_state == "resolved" else 16 if route_state == "unverified" else 0)
                + (30 if photo_state == "exact" else 18 if photo_state == "representative" else 0)
            ),
        )
        quality_band = (
            "strong"
            if quality_score >= 85
            else "good"
            if quality_score >= 70
            else "partial"
            if quality_score >= 50
            else "live_only"
        )

        return {
            "band": quality_band,
            "score": quality_score,
            "summary": FlightDetailsService._summarize_detail_quality(
                route_state=route_state,
                photo_state=photo_state,
                identity_score=identity_score,
            ),
            "route_state": route_state,
            "photo_state": photo_state,
            "photo_source": photo.get("source") if isinstance(photo, dict) else None,
            "identity_score": identity_score,
        }

    @staticmethod
    def _summarize_detail_quality(
        *,
        route_state: str,
        photo_state: str,
        identity_score: int,
    ) -> str:
        if route_state == "resolved" and photo_state == "exact":
            return "Resolved route with an exact aircraft photo."
        if route_state == "resolved" and photo_state == "representative":
            return "Resolved route with a representative aircraft photo."
        if route_state == "pending" and photo_state == "missing":
            return "Live track only. Route and photo are still missing."
        if route_state == "unverified":
            return "Route is plausible but still needs confirmation."
        if identity_score < 60:
            return "Identity metadata is still sparse for this aircraft."
        if photo_state == "missing":
            return "Resolved metadata without an aircraft photo yet."
        return "Live aircraft metadata is partially enriched."

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned
