from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import monotonic

from .provider_base import FlightProvider, FlightProviderError, FlightProviderRateLimitError


@dataclass(slots=True)
class SnapshotCacheEntry:
    payload: dict[str, object]
    expires_at: float
    provider_name: str | None = None


class FlightSnapshotService:
    def __init__(
        self,
        providers: list[FlightProvider],
        cache_ttl: float,
        cooldown_seconds: float,
        cache_path: str | None = None,
        archive_service=None,
        latest_cache_max_age_seconds: float = 150.0,
        latest_cache_stale_after_seconds: float = 120.0,
        provider_min_interval_seconds: float = 0.0,
    ) -> None:
        self.providers = providers
        self.cache_ttl = cache_ttl
        self.cooldown_seconds = cooldown_seconds
        self._cache: dict[tuple[float, float, float, float], SnapshotCacheEntry] = {}
        self._cooldown_until: dict[str, float] = {}
        self._lock = Lock()
        self._cache_path = Path(cache_path).expanduser() if cache_path else None
        self._archive_service = archive_service
        self.latest_cache_max_age_seconds = max(float(latest_cache_max_age_seconds or 0), 1.0)
        self.latest_cache_stale_after_seconds = max(float(latest_cache_stale_after_seconds or 0), 1.0)
        self.provider_min_interval_seconds = max(float(provider_min_interval_seconds or 0), 0.0)
        self._load_cache_from_disk()

    def get_flights(
        self,
        bbox: dict[str, float],
        *,
        prefer_latest_cache: bool = True,
        update_latest_cache: bool = True,
        provider_names: tuple[str, ...] | None = None,
        provider_min_interval_seconds: float | None = None,
    ) -> dict[str, object]:
        cache_key = self._cache_key(bbox)
        now = monotonic()

        if prefer_latest_cache:
            latest_payload = self._get_latest_cached_flights(bbox)
            if latest_payload is not None:
                return latest_payload

        with self._lock:
            cache_entry = self._cache.get(cache_key)

            if cache_entry and cache_entry.expires_at > now:
                return self._with_meta(
                    cache_entry.payload,
                    source="cache",
                    stale=False,
                    reason="cache_hit",
                    extra_meta=self._build_runtime_meta(
                        now,
                        provider_name=cache_entry.provider_name,
                    ),
                )

        payload, provider_name, fallback_reason, fallback_warning, last_error, diagnostics = self._fetch_from_providers(
            bbox,
            now,
            provider_names=provider_names,
            provider_min_interval_seconds=provider_min_interval_seconds,
        )
        if payload is None:
            if cache_entry:
                return self._build_stale_response(
                    cache_entry.payload,
                    reason=fallback_reason or "upstream_error",
                    warning=fallback_warning or "Upstream providers failed. Showing the last cached snapshot.",
                    extra_meta=diagnostics,
                )

            archived_payload = self._get_recent_archive_fallback(bbox)
            if archived_payload is not None:
                return self._build_stale_response(
                    archived_payload,
                    reason=fallback_reason or "upstream_error",
                    warning=(
                        "Live providers are temporarily unavailable. "
                        "Showing recently observed aircraft from the archive."
                    ),
                    extra_meta={
                        **diagnostics,
                        "fallback_source": "recent_archive_positions",
                    },
                )

            raise last_error or FlightProviderError("No upstream providers are currently available.")

        with self._lock:
            self._cache[cache_key] = SnapshotCacheEntry(
                payload=payload,
                expires_at=monotonic() + self.cache_ttl,
                provider_name=provider_name,
            )
            self._persist_cache_to_disk()

        if self._archive_service is not None:
            try:
                self._archive_service.store_snapshot(payload)
            except Exception:
                # Archiving is best-effort and must not break the live feed.
                pass
            if update_latest_cache:
                try:
                    self._archive_service.store_latest_snapshot(payload)
                except Exception:
                    pass

        return self._with_meta(
            payload,
            source="live",
            stale=False,
            reason="live",
            extra_meta=diagnostics,
        )

    def _fetch_from_providers(
        self,
        bbox: dict[str, float],
        now: float,
        *,
        provider_names: tuple[str, ...] | None = None,
        provider_min_interval_seconds: float | None = None,
    ) -> tuple[
        dict[str, object] | None,
        str | None,
        str | None,
        str | None,
        FlightProviderError | None,
        dict[str, object],
    ]:
        saw_cooldown = False
        saw_rate_limit = False
        last_error: FlightProviderError | None = None

        allowed_providers = set(provider_names) if provider_names is not None else None
        providers = [
            provider
            for provider in self.providers
            if allowed_providers is None or provider.name in allowed_providers
        ]
        for provider in providers:
            cooldown_until = self._cooldown_until.get(provider.name, 0)
            shared_wait = self._get_shared_provider_wait(provider.name)
            if cooldown_until > now or shared_wait > 0:
                saw_cooldown = True
                continue

            lease_acquired = self._acquire_shared_provider_lease(
                provider.name,
                min_interval_seconds=(
                    self.provider_min_interval_seconds
                    if provider_min_interval_seconds is None
                    else provider_min_interval_seconds
                ),
            )
            if not lease_acquired:
                saw_cooldown = True
                continue

            try:
                payload = provider.fetch_flights(bbox=bbox)
            except FlightProviderRateLimitError as exc:
                cooldown_seconds = max(
                    self.cooldown_seconds,
                    float(getattr(exc, "retry_after_seconds", 0) or 0),
                )
                with self._lock:
                    self._cooldown_until[provider.name] = monotonic() + cooldown_seconds
                self._finish_shared_provider_request(
                    provider.name,
                    cooldown_seconds=cooldown_seconds,
                )
                saw_rate_limit = True
                last_error = exc
                continue
            except FlightProviderError as exc:
                self._finish_shared_provider_request(provider.name)
                last_error = exc
                continue
            except Exception:
                self._finish_shared_provider_request(provider.name)
                raise

            with self._lock:
                self._cooldown_until.pop(provider.name, None)
            self._finish_shared_provider_request(provider.name, cooldown_seconds=0)
            provider_name = self._get_provider_label(provider)
            return payload, provider_name, None, None, None, self._build_runtime_meta(
                monotonic(),
                provider_name=provider_name,
            )

        if saw_rate_limit:
            return (
                None,
                None,
                "rate_limit",
                "Upstream provider rate limit exceeded. Showing the last cached snapshot.",
                last_error,
                self._build_runtime_meta(monotonic()),
            )
        if saw_cooldown:
            return (
                None,
                None,
                "cooldown",
                "Using cached snapshot while upstream providers cool down.",
                last_error,
                self._build_runtime_meta(monotonic()),
            )

        return (
            None,
            None,
            "upstream_error",
            None if last_error is None else str(last_error),
            last_error,
            self._build_runtime_meta(monotonic()),
        )

    @staticmethod
    def _build_stale_response(
        payload: dict[str, object],
        reason: str,
        warning: str,
        extra_meta: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return FlightSnapshotService._with_meta(
            payload,
            source="cache",
            stale=True,
            reason=reason,
            warning=warning,
            extra_meta=extra_meta,
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
                provider_name=entry.get("provider_name"),
            )

    def _persist_cache_to_disk(self) -> None:
        if not self._cache_path:
            return

        serializable_entries = [
            {
                "bbox_key": list(cache_key),
                "payload": cache_entry.payload,
                "provider_name": cache_entry.provider_name,
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
        extra_meta: dict[str, object] | None = None,
    ) -> dict[str, object]:
        response_payload = deepcopy(payload)
        response_payload["meta"] = {
            "source": source,
            "stale": stale,
            "reason": reason,
            "warning": warning,
            **FlightSnapshotService._build_quality_meta(payload),
        }
        if isinstance(extra_meta, dict):
            response_payload["meta"].update(extra_meta)
        return response_payload

    def _get_latest_cached_flights(self, bbox: dict[str, float]) -> dict[str, object] | None:
        if self._archive_service is None or not hasattr(self._archive_service, "list_latest_flights"):
            return None

        try:
            latest_payload = self._archive_service.list_latest_flights(
                bbox=bbox,
                max_age_seconds=self.latest_cache_max_age_seconds,
            )
        except Exception:
            return None

        if not latest_payload:
            return None

        cache_meta = latest_payload.get("cache_meta") if isinstance(latest_payload, dict) else None
        if not isinstance(cache_meta, dict) or not bool(cache_meta.get("collector_ready")):
            return None

        fetched_at = self._resolve_snapshot_timestamp(latest_payload.get("fetched_at"))
        snapshot_age_seconds = (
            float("inf")
            if fetched_at is None
            else max(0.0, datetime.now(timezone.utc).timestamp() - fetched_at)
        )
        is_stale = snapshot_age_seconds > self.latest_cache_stale_after_seconds
        warning = None
        if is_stale:
            warning = (
                "Showing the latest global snapshot; aircraft positions may have moved "
                f"since it was captured ({round(snapshot_age_seconds / 60)} min ago)."
            )

        return self._with_meta(
            latest_payload,
            source="collector_cache",
            stale=is_stale,
            reason="collector_cache_stale" if is_stale else "collector_cache_hit",
            warning=warning,
            extra_meta={
                **self._build_runtime_meta(monotonic()),
                **(cache_meta if isinstance(cache_meta, dict) else {}),
            },
        )

    def _get_recent_archive_fallback(self, bbox: dict[str, float]) -> dict[str, object] | None:
        if self._archive_service is None or not hasattr(self._archive_service, "list_latest_flights"):
            return None

        try:
            latest_payload = self._archive_service.list_latest_flights(
                bbox=bbox,
                max_age_seconds=self.latest_cache_max_age_seconds,
            )
        except Exception:
            return None

        if not isinstance(latest_payload, dict) or not latest_payload.get("flights"):
            return None

        cache_meta = latest_payload.get("cache_meta")
        if not isinstance(cache_meta, dict) or not cache_meta.get("fresh"):
            return None

        return latest_payload

    def _build_runtime_meta(
        self,
        now: float,
        provider_name: str | None = None,
    ) -> dict[str, object]:
        provider_quotas = {}
        for provider in self.providers:
            remaining = getattr(provider, "last_rate_limit_remaining", None)
            reset = getattr(provider, "last_rate_limit_reset", None)
            if remaining is None and reset is None:
                continue
            provider_quotas[self._get_provider_label(provider)] = {
                "remaining": remaining,
                "reset": reset,
            }

        meta = {
            "provider_used": provider_name,
            "providers_configured": [self._get_provider_label(provider) for provider in self.providers],
            "provider_cooldowns": self._active_cooldowns(now),
        }
        if provider_quotas:
            meta["provider_quotas"] = provider_quotas
        return meta

    def _active_cooldowns(self, now: float) -> dict[str, int]:
        cooldowns = {
            provider_name: max(1, round(cooldown_until - now))
            for provider_name, cooldown_until in self._cooldown_until.items()
            if cooldown_until > now
        }
        for provider in self.providers:
            if provider.name in cooldowns:
                continue
            shared_wait = self._get_shared_provider_cooldown(provider.name)
            if shared_wait > 0:
                cooldowns[provider.name] = max(1, round(shared_wait))
        return cooldowns

    def _get_shared_provider_wait(self, provider_name: str) -> float:
        if self._archive_service is None or not hasattr(self._archive_service, "provider_wait_seconds"):
            return 0.0
        try:
            return float(self._archive_service.provider_wait_seconds(provider_name) or 0.0)
        except Exception:
            return 0.0

    def _get_shared_provider_cooldown(self, provider_name: str) -> float:
        if self._archive_service is None or not hasattr(self._archive_service, "provider_cooldown_seconds"):
            return 0.0
        try:
            return float(self._archive_service.provider_cooldown_seconds(provider_name) or 0.0)
        except Exception:
            return 0.0

    def _acquire_shared_provider_lease(self, provider_name: str, min_interval_seconds: float) -> bool:
        if self._archive_service is None or not hasattr(self._archive_service, "try_acquire_provider_request"):
            return True
        try:
            acquired, _wait_seconds = self._archive_service.try_acquire_provider_request(
                provider_name,
                lease_seconds=120.0,
                min_interval_seconds=min_interval_seconds,
            )
            return bool(acquired)
        except Exception:
            return True

    def _finish_shared_provider_request(
        self,
        provider_name: str,
        cooldown_seconds: float | None = None,
    ) -> None:
        if self._archive_service is None or not hasattr(self._archive_service, "finish_provider_request"):
            return
        try:
            self._archive_service.finish_provider_request(
                provider_name,
                cooldown_seconds=cooldown_seconds,
            )
        except Exception:
            return

    @staticmethod
    def _build_quality_meta(payload: dict[str, object]) -> dict[str, object]:
        flights = [
            flight
            for flight in payload.get("flights") or []
            if isinstance(flight, dict)
        ]
        total = max(int(payload.get("count") or 0), len(flights))
        airspace_scope = FlightSnapshotService._classify_airspace_scope(payload.get("bbox"))

        if total <= 0:
            return {
                "airspace_scope": airspace_scope,
                "quality": {
                    "band": "empty",
                    "score": 0,
                    "summary": "No aircraft are currently visible in this airspace window.",
                    "identity": {
                        "registration_pct": 0,
                        "type_pct": 0,
                        "callsign_pct": 0,
                        "operator_pct": 0,
                    },
                    "traffic": {
                        "airborne": 0,
                        "ground": 0,
                        "fresh_contact_pct": 0,
                    },
                },
            }

        snapshot_timestamp = FlightSnapshotService._resolve_snapshot_timestamp(payload.get("fetched_at"))
        registration_count = sum(1 for flight in flights if FlightSnapshotService._has_text(flight.get("registration")))
        type_count = sum(1 for flight in flights if FlightSnapshotService._has_text(flight.get("type_code")))
        callsign_count = sum(1 for flight in flights if FlightSnapshotService._has_text(flight.get("callsign")))
        operator_count = sum(
            1
            for flight in flights
            if FlightSnapshotService._derive_operator_code(flight.get("callsign"))
        )
        airborne_count = sum(1 for flight in flights if not bool(flight.get("on_ground")))
        ground_count = max(0, total - airborne_count)
        fresh_contact_count = sum(
            1
            for flight in flights
            if FlightSnapshotService._is_recent_contact(flight.get("last_contact"), snapshot_timestamp)
        )

        registration_pct = FlightSnapshotService._calculate_pct(registration_count, total)
        type_pct = FlightSnapshotService._calculate_pct(type_count, total)
        callsign_pct = FlightSnapshotService._calculate_pct(callsign_count, total)
        operator_pct = FlightSnapshotService._calculate_pct(operator_count, total)
        fresh_contact_pct = FlightSnapshotService._calculate_pct(fresh_contact_count, total)
        quality_score = round(
            registration_pct * 0.25
            + type_pct * 0.2
            + callsign_pct * 0.15
            + operator_pct * 0.15
            + fresh_contact_pct * 0.25
        )
        quality_band = FlightSnapshotService._classify_quality_band(quality_score)

        return {
            "airspace_scope": airspace_scope,
            "quality": {
                "band": quality_band,
                "score": quality_score,
                "summary": FlightSnapshotService._summarize_quality(
                    quality_band=quality_band,
                    registration_pct=registration_pct,
                    type_pct=type_pct,
                    fresh_contact_pct=fresh_contact_pct,
                ),
                "identity": {
                    "registration_pct": registration_pct,
                    "type_pct": type_pct,
                    "callsign_pct": callsign_pct,
                    "operator_pct": operator_pct,
                },
                "traffic": {
                    "airborne": airborne_count,
                    "ground": ground_count,
                    "fresh_contact_pct": fresh_contact_pct,
                },
            },
        }

    @staticmethod
    def _get_provider_label(provider: FlightProvider) -> str:
        label = getattr(provider, "name", None) or getattr(provider, "label", None)
        if label:
            return str(label)
        return type(provider).__name__

    @staticmethod
    def _calculate_pct(count: int, total: int) -> int:
        if total <= 0:
            return 0
        return round((count / total) * 100)

    @staticmethod
    def _has_text(value: object) -> bool:
        if value is None:
            return False
        return bool(str(value).strip())

    @staticmethod
    def _derive_operator_code(callsign: object) -> str | None:
        cleaned = str(callsign or "").strip().upper()
        if len(cleaned) < 3 or not cleaned[:3].isalpha():
            return None
        return cleaned[:3]

    @staticmethod
    def _resolve_snapshot_timestamp(value: object) -> float | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _is_recent_contact(last_contact: object, snapshot_timestamp: float | None) -> bool:
        if snapshot_timestamp is None:
            return False
        try:
            contact_timestamp = float(last_contact)
        except (TypeError, ValueError):
            return False
        return snapshot_timestamp - contact_timestamp <= 30

    @staticmethod
    def _classify_quality_band(score: int) -> str:
        if score >= 85:
            return "strong"
        if score >= 70:
            return "good"
        if score >= 55:
            return "mixed"
        return "limited"

    @staticmethod
    def _summarize_quality(
        *,
        quality_band: str,
        registration_pct: int,
        type_pct: int,
        fresh_contact_pct: int,
    ) -> str:
        lead = {
            "strong": "Strong live coverage",
            "good": "Good live coverage",
            "mixed": "Mixed live coverage",
            "limited": "Thin live coverage",
        }.get(quality_band, "Live coverage")

        if registration_pct < 50:
            detail = "many aircraft still miss registrations"
        elif fresh_contact_pct < 65:
            detail = "positions are arriving with weaker freshness"
        elif type_pct < 75:
            detail = "type coverage is still patchy"
        else:
            detail = "identity data is well populated"

        return f"{lead}; {detail}."

    @staticmethod
    def _classify_airspace_scope(bbox: object) -> str:
        if not isinstance(bbox, dict):
            return "focused"

        try:
            lat_span = abs(float(bbox.get("lamax")) - float(bbox.get("lamin")))
            lon_span = abs(float(bbox.get("lomax")) - float(bbox.get("lomin")))
        except (TypeError, ValueError):
            return "focused"

        if lat_span >= 70 or lon_span >= 120:
            return "global"
        if lat_span >= 35 or lon_span >= 60:
            return "continental"
        if lat_span >= 12 or lon_span >= 18:
            return "regional"
        return "focused"
