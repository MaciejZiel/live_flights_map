from flask import Flask

from .config import Config
from .routes import api
from .services.adsb_lol import ADSBLolClient
from .services.adsb_lol_routes import ADSBLolRouteClient
from .services.aircraft_photos import AircraftPhotoService
from .services.airport_catalog import AirportCatalogService
from .services.airport_weather import AirportWeatherService
from .services.airport_workflow import AirportWorkflowService
from .services.diagnostics import DiagnosticsService
from .services.entity_search import EntitySearchService
from .services.flight_archive import FlightArchiveService
from .services.flight_details import FlightDetailsService
from .services.global_traffic_board import GlobalTrafficBoardService
from .services.flight_snapshot import FlightSnapshotService
from .services.openverse import OpenverseClient
from .services.opensky import OpenSkyClient
from .services.planespotting import PlanespottingClient
from .services.traffic_intelligence import TrafficIntelligenceService
from .services.wikimedia_commons import WikimediaCommonsClient
from .services.workspace import WorkspaceService


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())
    providers = []
    archive_service = FlightArchiveService(
        archive_path=app.config["FLIGHT_ARCHIVE_PATH"],
        retention_hours=app.config["FLIGHT_ARCHIVE_RETENTION_HOURS"],
        max_snapshots=app.config["FLIGHT_ARCHIVE_MAX_SNAPSHOTS"],
    )
    traffic_intelligence_service = TrafficIntelligenceService(
        archive_path=app.config["FLIGHT_ARCHIVE_PATH"],
    )
    airport_catalog_service = AirportCatalogService()
    workspace_service = WorkspaceService(
        workspace_path=app.config["WORKSPACE_DB_PATH"],
    )

    for provider_name in app.config["FLIGHT_DATA_PROVIDERS"]:
        if provider_name == "opensky":
            providers.append(
                OpenSkyClient(
                    base_url=app.config["OPENSKY_BASE_URL"],
                    username=app.config["OPENSKY_USERNAME"],
                    password=app.config["OPENSKY_PASSWORD"],
                    timeout=app.config["OPENSKY_TIMEOUT"],
                    max_retries=app.config["OPENSKY_RETRY_COUNT"],
                )
            )
            continue

        if provider_name == "adsb_lol":
            providers.append(
                ADSBLolClient(
                    base_url=app.config["ADSB_LOL_BASE_URL"],
                    timeout=app.config["ADSB_LOL_TIMEOUT"],
                    max_retries=app.config["ADSB_LOL_RETRY_COUNT"],
                    radius_limit_nm=app.config["ADSB_LOL_RADIUS_LIMIT_NM"],
                )
            )
            continue

        raise ValueError(f"Unsupported flight provider '{provider_name}'.")

    app.extensions["flight_snapshot_service"] = FlightSnapshotService(
        providers=providers,
        cache_ttl=app.config["OPENSKY_CACHE_TTL"],
        cooldown_seconds=app.config["OPENSKY_COOLDOWN_SECONDS"],
        cache_path=app.config["OPENSKY_CACHE_PATH"],
        archive_service=archive_service,
    )
    app.extensions["flight_archive_service"] = archive_service
    app.extensions["traffic_intelligence_service"] = traffic_intelligence_service
    app.extensions["airport_catalog_service"] = airport_catalog_service
    app.extensions["workspace_service"] = workspace_service
    app.extensions["global_traffic_board_service"] = GlobalTrafficBoardService(
        snapshot_service=app.extensions["flight_snapshot_service"],
        archive_service=archive_service,
        cache_ttl=app.config["GLOBAL_TRAFFIC_BOARD_CACHE_TTL"],
        lookback_minutes=app.config["GLOBAL_TRAFFIC_BOARD_LOOKBACK_MINUTES"],
    )
    app.extensions["flight_details_service"] = FlightDetailsService(
        route_client=ADSBLolRouteClient(
            base_url=app.config["ADSB_LOL_ROUTE_API_URL"],
            timeout=app.config["ADSB_LOL_ROUTE_TIMEOUT"],
            max_retries=app.config["ADSB_LOL_ROUTE_RETRY_COUNT"],
        ),
        photo_client=AircraftPhotoService(
            providers=[
                PlanespottingClient(
                    base_url=app.config["PLANESPOTTING_BASE_URL"],
                    timeout=app.config["PLANESPOTTING_TIMEOUT"],
                    max_retries=app.config["PLANESPOTTING_RETRY_COUNT"],
                ),
                WikimediaCommonsClient(
                    base_url=app.config["WIKIMEDIA_COMMONS_BASE_URL"],
                    timeout=app.config["WIKIMEDIA_COMMONS_TIMEOUT"],
                    max_retries=app.config["WIKIMEDIA_COMMONS_RETRY_COUNT"],
                ),
                OpenverseClient(
                    base_url=app.config["OPENVERSE_BASE_URL"],
                    timeout=app.config["OPENVERSE_TIMEOUT"],
                    max_retries=app.config["OPENVERSE_RETRY_COUNT"],
                ),
            ]
        ),
        cache_ttl=app.config["FLIGHT_DETAILS_CACHE_TTL"],
    )
    app.extensions["entity_search_service"] = EntitySearchService(
        archive_service=archive_service,
        airport_catalog_service=airport_catalog_service,
        traffic_intelligence_service=traffic_intelligence_service,
        lookback_hours=app.config["FLIGHT_SEARCH_LOOKBACK_HOURS"],
    )
    app.extensions["airport_workflow_service"] = AirportWorkflowService(
        airport_catalog_service=airport_catalog_service,
        traffic_intelligence_service=traffic_intelligence_service,
        snapshot_service=app.extensions["flight_snapshot_service"],
    )
    app.extensions["airport_weather_service"] = AirportWeatherService(
        base_url=app.config["AIRPORT_WEATHER_BASE_URL"],
        timeout=app.config["AIRPORT_WEATHER_TIMEOUT"],
        cache_ttl=app.config["AIRPORT_WEATHER_CACHE_TTL"],
    )
    app.extensions["diagnostics_service"] = DiagnosticsService(
        snapshot_service=app.extensions["flight_snapshot_service"],
        archive_service=archive_service,
        workspace_service=workspace_service,
    )
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def healthcheck():
        return app.extensions["diagnostics_service"].build_healthcheck()

    return app
