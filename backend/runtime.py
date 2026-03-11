from __future__ import annotations

from dataclasses import dataclass

from flask import Flask

from .config import Config
from .routes import api
from .services.adsb_lol import ADSBLolClient
from .services.adsb_lol_routes import ADSBLolRouteClient
from .services.aircraft_photo_proxy import AircraftPhotoProxyService
from .services.aircraft_photos import AircraftPhotoService
from .services.airport_catalog import AirportCatalogService
from .services.airport_weather import AirportWeatherService
from .services.airport_workflow import AirportWorkflowService
from .services.alerts_worker import AlertSweepService
from .services.diagnostics import DiagnosticsService
from .services.entity_search import EntitySearchService
from .services.flight_archive import FlightArchiveService
from .services.flight_details import FlightDetailsService
from .services.flight_snapshot import FlightSnapshotService
from .services.global_traffic_board import GlobalTrafficBoardService
from .services.openverse import OpenverseClient
from .services.opensky import OpenSkyClient
from .services.planespotting import PlanespottingClient
from .services.snapshot_collector import SnapshotCollectorService
from .services.traffic_intelligence import TrafficIntelligenceService
from .services.wikimedia_commons import WikimediaCommonsClient
from .services.workspace import WorkspaceService


@dataclass(slots=True)
class BackendRuntime:
    config: object
    flight_snapshot_service: FlightSnapshotService
    flight_archive_service: FlightArchiveService
    traffic_intelligence_service: TrafficIntelligenceService
    airport_catalog_service: AirportCatalogService
    workspace_service: WorkspaceService
    global_traffic_board_service: GlobalTrafficBoardService
    flight_details_service: FlightDetailsService
    aircraft_photo_proxy_service: AircraftPhotoProxyService
    entity_search_service: EntitySearchService
    airport_workflow_service: AirportWorkflowService
    airport_weather_service: AirportWeatherService
    diagnostics_service: DiagnosticsService
    snapshot_collector_service: SnapshotCollectorService
    alert_sweep_service: AlertSweepService


def build_runtime(config: object | None = None) -> BackendRuntime:
    config = config or Config()
    providers = []
    archive_service = FlightArchiveService(
        archive_path=config.FLIGHT_ARCHIVE_PATH,
        retention_hours=config.FLIGHT_ARCHIVE_RETENTION_HOURS,
        max_snapshots=config.FLIGHT_ARCHIVE_MAX_SNAPSHOTS,
    )
    traffic_intelligence_service = TrafficIntelligenceService(
        archive_path=config.FLIGHT_ARCHIVE_PATH,
    )
    airport_catalog_service = AirportCatalogService()
    workspace_service = WorkspaceService(
        workspace_path=config.WORKSPACE_DB_PATH,
    )

    for provider_name in config.FLIGHT_DATA_PROVIDERS:
        if provider_name == "opensky":
            providers.append(
                OpenSkyClient(
                    base_url=config.OPENSKY_BASE_URL,
                    username=config.OPENSKY_USERNAME,
                    password=config.OPENSKY_PASSWORD,
                    timeout=config.OPENSKY_TIMEOUT,
                    max_retries=config.OPENSKY_RETRY_COUNT,
                )
            )
            continue

        if provider_name == "adsb_lol":
            providers.append(
                ADSBLolClient(
                    base_url=config.ADSB_LOL_BASE_URL,
                    timeout=config.ADSB_LOL_TIMEOUT,
                    max_retries=config.ADSB_LOL_RETRY_COUNT,
                    radius_limit_nm=config.ADSB_LOL_RADIUS_LIMIT_NM,
                )
            )
            continue

        raise ValueError(f"Unsupported flight provider '{provider_name}'.")

    flight_snapshot_service = FlightSnapshotService(
        providers=providers,
        cache_ttl=config.OPENSKY_CACHE_TTL,
        cooldown_seconds=config.OPENSKY_COOLDOWN_SECONDS,
        cache_path=config.OPENSKY_CACHE_PATH,
        archive_service=archive_service,
    )
    global_traffic_board_service = GlobalTrafficBoardService(
        snapshot_service=flight_snapshot_service,
        archive_service=archive_service,
        cache_ttl=config.GLOBAL_TRAFFIC_BOARD_CACHE_TTL,
        lookback_minutes=config.GLOBAL_TRAFFIC_BOARD_LOOKBACK_MINUTES,
    )
    flight_details_service = FlightDetailsService(
        route_client=ADSBLolRouteClient(
            base_url=config.ADSB_LOL_ROUTE_API_URL,
            timeout=config.ADSB_LOL_ROUTE_TIMEOUT,
            max_retries=config.ADSB_LOL_ROUTE_RETRY_COUNT,
        ),
        photo_client=AircraftPhotoService(
            providers=[
                PlanespottingClient(
                    base_url=config.PLANESPOTTING_BASE_URL,
                    timeout=config.PLANESPOTTING_TIMEOUT,
                    max_retries=config.PLANESPOTTING_RETRY_COUNT,
                ),
                WikimediaCommonsClient(
                    base_url=config.WIKIMEDIA_COMMONS_BASE_URL,
                    timeout=config.WIKIMEDIA_COMMONS_TIMEOUT,
                    max_retries=config.WIKIMEDIA_COMMONS_RETRY_COUNT,
                ),
                OpenverseClient(
                    base_url=config.OPENVERSE_BASE_URL,
                    timeout=config.OPENVERSE_TIMEOUT,
                    max_retries=config.OPENVERSE_RETRY_COUNT,
                ),
            ]
        ),
        cache_ttl=config.FLIGHT_DETAILS_CACHE_TTL,
    )
    aircraft_photo_proxy_service = AircraftPhotoProxyService(
        timeout=config.AIRCRAFT_PHOTO_PROXY_TIMEOUT,
        allowed_hosts=config.AIRCRAFT_PHOTO_PROXY_ALLOWED_HOSTS,
    )
    entity_search_service = EntitySearchService(
        archive_service=archive_service,
        airport_catalog_service=airport_catalog_service,
        traffic_intelligence_service=traffic_intelligence_service,
        lookback_hours=config.FLIGHT_SEARCH_LOOKBACK_HOURS,
    )
    airport_workflow_service = AirportWorkflowService(
        airport_catalog_service=airport_catalog_service,
        traffic_intelligence_service=traffic_intelligence_service,
        snapshot_service=flight_snapshot_service,
    )
    airport_weather_service = AirportWeatherService(
        base_url=config.AIRPORT_WEATHER_BASE_URL,
        timeout=config.AIRPORT_WEATHER_TIMEOUT,
        cache_ttl=config.AIRPORT_WEATHER_CACHE_TTL,
    )
    diagnostics_service = DiagnosticsService(
        snapshot_service=flight_snapshot_service,
        archive_service=archive_service,
        workspace_service=workspace_service,
    )
    snapshot_collector_service = SnapshotCollectorService(
        snapshot_service=flight_snapshot_service,
        traffic_intelligence_service=traffic_intelligence_service,
    )
    alert_sweep_service = AlertSweepService(
        snapshot_service=flight_snapshot_service,
        traffic_intelligence_service=traffic_intelligence_service,
        workspace_service=workspace_service,
    )

    return BackendRuntime(
        config=config,
        flight_snapshot_service=flight_snapshot_service,
        flight_archive_service=archive_service,
        traffic_intelligence_service=traffic_intelligence_service,
        airport_catalog_service=airport_catalog_service,
        workspace_service=workspace_service,
        global_traffic_board_service=global_traffic_board_service,
        flight_details_service=flight_details_service,
        aircraft_photo_proxy_service=aircraft_photo_proxy_service,
        entity_search_service=entity_search_service,
        airport_workflow_service=airport_workflow_service,
        airport_weather_service=airport_weather_service,
        diagnostics_service=diagnostics_service,
        snapshot_collector_service=snapshot_collector_service,
        alert_sweep_service=alert_sweep_service,
    )


def bind_runtime(app: Flask, runtime: BackendRuntime) -> Flask:
    app.config.from_object(runtime.config)
    app.extensions["flight_snapshot_service"] = runtime.flight_snapshot_service
    app.extensions["flight_archive_service"] = runtime.flight_archive_service
    app.extensions["traffic_intelligence_service"] = runtime.traffic_intelligence_service
    app.extensions["airport_catalog_service"] = runtime.airport_catalog_service
    app.extensions["workspace_service"] = runtime.workspace_service
    app.extensions["global_traffic_board_service"] = runtime.global_traffic_board_service
    app.extensions["flight_details_service"] = runtime.flight_details_service
    app.extensions["aircraft_photo_proxy_service"] = runtime.aircraft_photo_proxy_service
    app.extensions["entity_search_service"] = runtime.entity_search_service
    app.extensions["airport_workflow_service"] = runtime.airport_workflow_service
    app.extensions["airport_weather_service"] = runtime.airport_weather_service
    app.extensions["diagnostics_service"] = runtime.diagnostics_service
    app.extensions["snapshot_collector_service"] = runtime.snapshot_collector_service
    app.extensions["alert_sweep_service"] = runtime.alert_sweep_service
    return app


def create_api_app(config: object | None = None, runtime: BackendRuntime | None = None) -> Flask:
    runtime = runtime or build_runtime(config)
    app = Flask(__name__)
    bind_runtime(app, runtime)
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def healthcheck():
        return app.extensions["diagnostics_service"].build_healthcheck()

    return app
