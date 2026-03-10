from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic

from .provider_base import FlightProvider, FlightProviderError, FlightProviderRateLimitError


@dataclass(slots=True)
class SnapshotCacheEntry:
    payload: dict[str, object]
    expires_at: float


class FlightSnapshotService:
    def __init__(
        self,
        providers: list[FlightProvider],
        cache_ttl: float,
        cooldown_seconds: float,
        cache_path: str | None = None,
        archive_service=None,
    ) -> None:
        self.providers = providers
        self.cache_ttl = cache_ttl
        self.cooldown_seconds = cooldown_seconds
        self._cache: dict[tuple[float, float, float, float], SnapshotCacheEntry] = {}
        self._cooldown_until: dict[tuple[str, tuple[float, float, float, float]], float] = {}
        self._lock = Lock()
        self._cache_path = Path(cache_path).expanduser() if cache_path else None
        self._archive_service = archive_service
        self._load_cache_from_disk()

    def get_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        cache_key = self._cache_key(bbox)
        now = monotonic()

        with self._lock:
            cache_entry = self._cache.get(cache_key)

            if cache_entry and cache_entry.expires_at > now:
                return self._with_meta(
                    cache_entry.payload,
                    source="cache",
                    stale=False,
                    reason="cache_hit",
                )

        payload, fallback_reason, fallback_warning, last_error = self._fetch_from_providers(bbox, cache_key, now)
        if payload is None:
            if cache_entry:
                return self._build_stale_response(
                    cache_entry.payload,
                    reason=fallback_reason or "upstream_error",
                    warning=fallback_warning or "Upstream providers failed. Showing the last cached snapshot.",
                )
            raise last_error or FlightProviderError("No upstream providers are currently available.")

        with self._lock:
            self._cache[cache_key] = SnapshotCacheEntry(
                payload=payload,
                expires_at=monotonic() + self.cache_ttl,
            )
            self._persist_cache_to_disk()

        if self._archive_service is not None:
            try:
                self._archive_service.store_snapshot(payload)
            except Exception:
                # Archiving is best-effort and must not break the live feed.
                pass

        return self._with_meta(payload, source="live", stale=False, reason="live")

    def _fetch_from_providers(
        self,
        bbox: dict[str, float],
        cache_key: tuple[float, float, float, float],
        now: float,
    ) -> tuple[dict[str, object] | None, str | None, str | None, FlightProviderError | None]:
        saw_cooldown = False
        saw_rate_limit = False
        last_error: FlightProviderError | None = None

        for provider in self.providers:
            provider_cooldown_key = (provider.name, cache_key)
            cooldown_until = self._cooldown_until.get(provider_cooldown_key, 0)
            if cooldown_until > now:
                saw_cooldown = True
                continue

            try:
                payload = provider.fetch_flights(bbox=bbox)
            except FlightProviderRateLimitError as exc:
                with self._lock:
                    self._cooldown_until[provider_cooldown_key] = monotonic() + self.cooldown_seconds
                saw_rate_limit = True
                last_error = exc
                continue
            except FlightProviderError as exc:
                last_error = exc
                continue

            with self._lock:
                self._cooldown_until.pop(provider_cooldown_key, None)
            return payload, None, None, None

        if saw_rate_limit:
            return None, "rate_limit", "Upstream provider rate limit exceeded. Showing the last cached snapshot.", last_error
        if saw_cooldown:
            return None, "cooldown", "Using cached snapshot while upstream providers cool down.", last_error

        return None, "upstream_error", None if last_error is None else str(last_error), last_error

    @staticmethod
    def _build_stale_response(
        payload: dict[str, object],
        reason: str,
        warning: str,
    ) -> dict[str, object]:
        return FlightSnapshotService._with_meta(
            payload,
            source="cache",
            stale=True,
            reason=reason,
            warning=warning,
        )

    @staticmethod
    def _cache_key(bbox: dict[str, float]) -> tuple[float, float, float, float]:
        return (
            round(bbox["lamin"], 4),
            round(bbox["lamax"], 4),
            round(bbox["lomin"], 4),
            round(bbox["lomax"], 4),
        )

    def _load_cache_from_disk(self) -> None:
        if not self._cache_path or not self._cache_path.exists():
            return

        try:
            raw_payload = json.loads(self._cache_path.read_text())
        except (OSError, json.JSONDecodeError):
            return

        entries = raw_payload.get("entries", [])
        for entry in entries:
            bbox_key = entry.get("bbox_key")
            payload = entry.get("payload")
            if not isinstance(bbox_key, list) or len(bbox_key) != 4 or not isinstance(payload, dict):
                continue

            try:
                cache_key = tuple(float(value) for value in bbox_key)
            except (TypeError, ValueError):
                continue

            self._cache[cache_key] = SnapshotCacheEntry(
                payload=payload,
                expires_at=0,
            )

    def _persist_cache_to_disk(self) -> None:
        if not self._cache_path:
            return

        serializable_entries = [
            {
                "bbox_key": list(cache_key),
                "payload": cache_entry.payload,
            }
            for cache_key, cache_entry in self._cache.items()
        ]

        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps({"entries": serializable_entries}))
        except OSError:
            return

    @staticmethod
    def _with_meta(
        payload: dict[str, object],
        source: str,
        stale: bool,
        reason: str,
        warning: str | None = None,
    ) -> dict[str, object]:
        response_payload = deepcopy(payload)
        response_payload["meta"] = {
            "source": source,
            "stale": stale,
            "reason": reason,
            "warning": warning,
        }
        return response_payload
