from __future__ import annotations

from datetime import datetime, timezone

from .global_traffic_board import GlobalTrafficBoardService
from .provider_base import FlightProviderError


class SnapshotCollectorService:
    DEFAULT_SECTORS = (
        {
            "key": "global_world",
            "bbox": {"lamin": -90.0, "lamax": 90.0, "lomin": -180.0, "lomax": 180.0},
            "provider_names": ("opensky",),
        },
        {
            "key": "poland_focus",
            "bbox": {"lamin": 49.0, "lamax": 55.1, "lomin": 14.0, "lomax": 24.5},
        },
        {
            "key": "north_atlantic",
            "bbox": {"lamin": 35.0, "lamax": 68.0, "lomin": -52.0, "lomax": -11.0},
        },
        *GlobalTrafficBoardService.SECTORS,
        {
            "key": "north_pacific_west",
            "bbox": {"lamin": 18.0, "lamax": 62.0, "lomin": 140.0, "lomax": 180.0},
        },
        {
            "key": "north_pacific_east",
            "bbox": {"lamin": 18.0, "lamax": 62.0, "lomin": -180.0, "lomax": -120.0},
        },
    )

    @classmethod
    def select_sectors(cls, configured_keys: tuple[str, ...]) -> tuple[dict[str, object], ...]:
        if "*" in configured_keys:
            return (next(sector for sector in cls.DEFAULT_SECTORS if sector["key"] == "global_world"),)

        sectors_by_key = {str(sector["key"]): sector for sector in cls.DEFAULT_SECTORS}
        unknown_keys = sorted(set(configured_keys) - sectors_by_key.keys())
        if unknown_keys:
            raise ValueError(f"Unknown snapshot collector sector(s): {', '.join(unknown_keys)}")

        return tuple(sectors_by_key[key] for key in configured_keys)

    def __init__(
        self,
        snapshot_service,
        traffic_intelligence_service=None,
        archive_service=None,
        sectors: tuple[dict[str, object], ...] | None = None,
    ) -> None:
        self.snapshot_service = snapshot_service
        self.traffic_intelligence_service = traffic_intelligence_service
        self.archive_service = archive_service
        self.sectors = self.DEFAULT_SECTORS if sectors is None else sectors

    def collect_once(self) -> dict[str, object]:
        started_at = datetime.now(timezone.utc)
        warnings: list[str] = []
        sectors_synced = 0
        flights_collected = 0
        enriched_flights = 0
        latest_positions_stored = 0
        sector_results: list[dict[str, object]] = []

        for sector in self.sectors:
            sector_started_at = datetime.now(timezone.utc)
            try:
                payload = self.snapshot_service.get_flights(
                    sector["bbox"],
                    prefer_latest_cache=False,
                    update_latest_cache=False,
                    provider_names=sector.get("provider_names"),
                )
            except FlightProviderError as exc:
                warnings.append(f"{sector['key']}: {exc}")
                sector_results.append(
                    {
                        "key": sector["key"],
                        "bbox": sector["bbox"],
                        "started_at": sector_started_at.isoformat(),
                        "status": "error",
                        "warning": str(exc),
                        "flight_count": 0,
                        "latest_positions_stored": 0,
                    }
                )
                continue

            flights = [flight for flight in payload.get("flights") or [] if isinstance(flight, dict)]
            sector_meta = payload.get("meta") if isinstance(payload, dict) else None
            if isinstance(sector_meta, dict) and sector_meta.get("stale"):
                warning = str(
                    sector_meta.get("warning")
                    or "Provider data is stale; waiting for a fresh snapshot."
                )
                warnings.append(f"{sector['key']}: {warning}")
                sector_results.append(
                    {
                        "key": sector["key"],
                        "bbox": sector["bbox"],
                        "started_at": sector_started_at.isoformat(),
                        "fetched_at": payload.get("fetched_at"),
                        "status": "stale",
                        "warning": warning,
                        "source": sector_meta.get("source"),
                        "provider_used": sector_meta.get("provider_used"),
                        "flight_count": len(flights),
                        "latest_positions_stored": 0,
                    }
                )
                continue

            sectors_synced += 1
            flights_collected += len(flights)
            stored_flights = flights

            if self.traffic_intelligence_service is not None and flights:
                try:
                    enriched = self.traffic_intelligence_service.enrich_flights(flights)
                except Exception:
                    enriched = flights

                stored_flights = [flight for flight in enriched if isinstance(flight, dict)]
                enriched_flights += sum(
                    1
                    for flight in stored_flights
                    if isinstance(flight, dict) and flight.get("intelligence_updated_at")
                )

            if self.archive_service is not None and stored_flights:
                try:
                    cache_result = self.archive_service.store_latest_snapshot(
                        {
                            **payload,
                            "count": len(stored_flights),
                            "flights": stored_flights,
                        },
                        sector_key=str(sector.get("key") or "").strip() or None,
                    )
                except Exception:
                    cache_result = {"stored": 0}
                latest_positions_stored += int(cache_result.get("stored") or 0)

            sector_results.append(
                {
                    "key": sector["key"],
                    "bbox": sector["bbox"],
                    "started_at": sector_started_at.isoformat(),
                    "fetched_at": payload.get("fetched_at"),
                    "status": "ok",
                    "source": None if not isinstance(sector_meta, dict) else sector_meta.get("source"),
                    "provider_used": None
                    if not isinstance(sector_meta, dict)
                    else sector_meta.get("provider_used"),
                    "flight_count": len(stored_flights),
                    "latest_positions_stored": int(cache_result.get("stored") or 0)
                    if self.archive_service is not None and stored_flights
                    else 0,
                    "quality": None if not isinstance(sector_meta, dict) else sector_meta.get("quality"),
                }
            )

        payload = {
            "started_at": started_at.isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "sectors_total": len(self.sectors),
            "sectors_synced": sectors_synced,
            "flights_collected": flights_collected,
            "intelligence_enriched": enriched_flights,
            "latest_positions_stored": latest_positions_stored,
            "warnings": warnings,
            "sectors": sector_results,
        }
        if self.archive_service is not None and hasattr(self.archive_service, "record_collector_run"):
            try:
                self.archive_service.record_collector_run(payload)
            except Exception:
                pass
        return payload
