from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

from .provider_base import FlightProviderError


@dataclass(slots=True)
class GlobalBoardCacheEntry:
    payload: dict[str, object]
    expires_at: float


class GlobalTrafficBoardService:
    SECTORS = (
        {
            "key": "north_america_west",
            "bbox": {"lamin": 24.0, "lamax": 58.0, "lomin": -136.0, "lomax": -102.0},
        },
        {
            "key": "north_america_east",
            "bbox": {"lamin": 20.0, "lamax": 58.0, "lomin": -102.0, "lomax": -52.0},
        },
        {
            "key": "south_america",
            "bbox": {"lamin": -56.0, "lamax": 14.0, "lomin": -84.0, "lomax": -34.0},
        },
        {
            "key": "europe",
            "bbox": {"lamin": 35.0, "lamax": 71.0, "lomin": -11.0, "lomax": 35.0},
        },
        {
            "key": "africa_middle_east",
            "bbox": {"lamin": -35.0, "lamax": 38.0, "lomin": -20.0, "lomax": 60.0},
        },
        {
            "key": "south_asia",
            "bbox": {"lamin": 5.0, "lamax": 47.0, "lomin": 60.0, "lomax": 102.0},
        },
        {
            "key": "east_asia_oceania",
            "bbox": {"lamin": -12.0, "lamax": 56.0, "lomin": 102.0, "lomax": 168.0},
        },
    )

    def __init__(
        self,
        snapshot_service,
        archive_service,
        cache_ttl: float,
        lookback_minutes: int,
    ) -> None:
        self.snapshot_service = snapshot_service
        self.archive_service = archive_service
        self.cache_ttl = max(cache_ttl, 15.0)
        self.lookback_minutes = max(int(lookback_minutes), 15)
        self._cache: dict[int, GlobalBoardCacheEntry] = {}
        self._lock = Lock()

    def get_board(self, limit: int) -> dict[str, object]:
        normalized_limit = min(max(limit, 1), 20)
        now = monotonic()

        with self._lock:
            cache_entry = self._cache.get(normalized_limit)
            if cache_entry and cache_entry.expires_at > now:
                return deepcopy(cache_entry.payload)

        payload = self._build_board(normalized_limit, cache_entry.payload if cache_entry else None)

        with self._lock:
            self._cache[normalized_limit] = GlobalBoardCacheEntry(
                payload=payload,
                expires_at=monotonic() + self.cache_ttl,
            )

        return deepcopy(payload)

    def _build_board(
        self,
        limit: int,
        stale_payload: dict[str, object] | None,
    ) -> dict[str, object]:
        merged_flights: dict[str, dict[str, object]] = {}
        warnings: list[str] = []
        source_counts = {"live": 0, "cache": 0}

        for sector in self.SECTORS:
            try:
                sector_payload = self.snapshot_service.get_flights(sector["bbox"])
            except FlightProviderError as exc:
                warnings.append(f"{sector['key']}: {exc}")
                continue

            meta = sector_payload.get("meta") or {}
            source = str(meta.get("source") or "live")
            source_counts[source if source in source_counts else "live"] += 1
            warning = meta.get("warning")
            if warning:
                warnings.append(str(warning))

            for flight in sector_payload.get("flights") or []:
                if not isinstance(flight, dict):
                    continue

                icao24 = str(flight.get("icao24") or "").strip().lower()
                if not icao24:
                    continue

                candidate = {
                    **flight,
                    "icao24": icao24,
                    "board_sector": sector["key"],
                }
                existing = merged_flights.get(icao24)
                if existing is None or self._is_better_candidate(candidate, existing):
                    merged_flights[icao24] = candidate

        if not merged_flights:
            if stale_payload:
                stale_copy = deepcopy(stale_payload)
                stale_meta = dict(stale_copy.get("meta") or {})
                stale_meta["stale"] = True
                stale_meta["warning"] = (
                    "Global traffic board is temporarily unavailable. Showing the most recent board snapshot."
                )
                stale_copy["meta"] = stale_meta
                return stale_copy

            if warnings:
                raise FlightProviderError("; ".join(warnings))

            return {
                "count": 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "flights": [],
                "meta": {
                    "coverage": "global",
                    "sectors_synced": 0,
                    "sectors_total": len(self.SECTORS),
                    "source": "unavailable",
                    "warning": None,
                    "stale": False,
                },
            }

        hot_payload = self.archive_service.list_hot_flights(
            limit=max(limit * 6, 18),
            lookback_minutes=self.lookback_minutes,
        )
        hot_counts = {
            str(flight.get("icao24") or "").strip().lower(): int(flight.get("tracking_count") or 0)
            for flight in hot_payload.get("flights") or []
            if isinstance(flight, dict)
        }

        ranked_flights = sorted(
            (
                {
                    **flight,
                    "tracking_count": hot_counts.get(icao24, 0),
                    "tracking_score": self._tracking_score(flight, hot_counts.get(icao24, 0)),
                }
                for icao24, flight in merged_flights.items()
            ),
            key=lambda flight: (
                float(flight.get("tracking_score") or 0),
                -float(flight.get("last_contact") or 999999),
            ),
            reverse=True,
        )[:limit]

        return {
            "count": len(ranked_flights),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "flights": ranked_flights,
            "meta": {
                "coverage": "global",
                "sectors_synced": sum(source_counts.values()),
                "sectors_total": len(self.SECTORS),
                "source": "live" if source_counts["live"] else "cache",
                "warning": warnings[0] if warnings else None,
                "stale": False,
                "lookback_minutes": self.lookback_minutes,
            },
        }

    @staticmethod
    def _is_better_candidate(candidate: dict[str, object], existing: dict[str, object]) -> bool:
        candidate_last_contact = candidate.get("last_contact")
        existing_last_contact = existing.get("last_contact")

        if isinstance(candidate_last_contact, int) and isinstance(existing_last_contact, int):
            if candidate_last_contact != existing_last_contact:
                return candidate_last_contact < existing_last_contact

        if bool(candidate.get("on_ground")) != bool(existing.get("on_ground")):
            return not bool(candidate.get("on_ground"))

        return float(candidate.get("velocity") or 0) > float(existing.get("velocity") or 0)

    @staticmethod
    def _tracking_score(flight: dict[str, object], tracking_count: int) -> float:
        freshness_score = max(0.0, 900.0 - min(float(flight.get("last_contact") or 900), 900.0))
        speed_score = max(float(flight.get("velocity") or 0), 0.0) * 3.6
        altitude_score = max(float(flight.get("altitude") or 0), 0.0) / 1000
        airborne_bonus = 500.0 if not bool(flight.get("on_ground")) else 0.0
        return tracking_count * 10000.0 + freshness_score * 3.0 + speed_score + altitude_score + airborne_bonus
