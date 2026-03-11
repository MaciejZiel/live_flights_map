from __future__ import annotations

from datetime import datetime, timezone

from .global_traffic_board import GlobalTrafficBoardService
from .provider_base import FlightProviderError


class SnapshotCollectorService:
    DEFAULT_SECTORS = (
        {
            "key": "poland_focus",
            "bbox": {"lamin": 49.0, "lamax": 55.1, "lomin": 14.0, "lomax": 24.5},
        },
        *GlobalTrafficBoardService.SECTORS,
    )

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
        self.sectors = sectors or self.DEFAULT_SECTORS

    def collect_once(self) -> dict[str, object]:
        warnings: list[str] = []
        sectors_synced = 0
        flights_collected = 0
        enriched_flights = 0
        latest_positions_stored = 0

        for sector in self.sectors:
            try:
                payload = self.snapshot_service.get_flights(
                    sector["bbox"],
                    prefer_latest_cache=False,
                    update_latest_cache=False,
                )
            except FlightProviderError as exc:
                warnings.append(f"{sector['key']}: {exc}")
                continue

            sectors_synced += 1
            flights = [flight for flight in payload.get("flights") or [] if isinstance(flight, dict)]
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

        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sectors_total": len(self.sectors),
            "sectors_synced": sectors_synced,
            "flights_collected": flights_collected,
            "intelligence_enriched": enriched_flights,
            "latest_positions_stored": latest_positions_stored,
            "warnings": warnings,
        }
