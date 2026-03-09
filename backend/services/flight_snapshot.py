from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from .opensky import OpenSkyClient, OpenSkyError, OpenSkyRateLimitError


@dataclass(slots=True)
class SnapshotCacheEntry:
    payload: dict[str, object]
    expires_at: float


class FlightSnapshotService:
    def __init__(
        self,
        client: OpenSkyClient,
        cache_ttl: float,
        cooldown_seconds: float,
    ) -> None:
        self.client = client
        self.cache_ttl = cache_ttl
        self.cooldown_seconds = cooldown_seconds
        self._cache: dict[tuple[float, float, float, float], SnapshotCacheEntry] = {}
        self._cooldown_until: dict[tuple[float, float, float, float], float] = {}
        self._lock = Lock()

    def get_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        cache_key = self._cache_key(bbox)
        now = monotonic()

        with self._lock:
            cache_entry = self._cache.get(cache_key)
            cooldown_until = self._cooldown_until.get(cache_key, 0)

            if cache_entry and cache_entry.expires_at > now:
                return self._with_meta(
                    cache_entry.payload,
                    source="cache",
                    stale=False,
                    reason="cache_hit",
                )

        if cooldown_until > now:
            if cache_entry:
                retry_after = max(1, int(cooldown_until - now))
                return self._build_stale_response(
                    cache_entry.payload,
                    reason="cooldown",
                    warning=f"Using cached snapshot while OpenSky cools down ({retry_after}s left).",
                )
            raise OpenSkyError("OpenSky cooldown is active. Try again in a few seconds.")

        try:
            payload = self.client.fetch_flights(bbox=bbox)
        except OpenSkyRateLimitError as exc:
            with self._lock:
                self._cooldown_until[cache_key] = monotonic() + self.cooldown_seconds

            if cache_entry:
                return self._build_stale_response(
                    cache_entry.payload,
                    reason="rate_limit",
                    warning="OpenSky rate limit exceeded. Showing the last cached snapshot.",
                )

            raise exc
        except OpenSkyError as exc:
            if cache_entry:
                return self._build_stale_response(
                    cache_entry.payload,
                    reason="upstream_error",
                    warning=f"{exc} Showing the last cached snapshot.",
                )
            raise

        with self._lock:
            self._cache[cache_key] = SnapshotCacheEntry(
                payload=payload,
                expires_at=monotonic() + self.cache_ttl,
            )
            self._cooldown_until.pop(cache_key, None)

        return self._with_meta(payload, source="live", stale=False, reason="live")

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
