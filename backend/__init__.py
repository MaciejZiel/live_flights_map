from flask import Flask

from .config import Config
from .routes import api
from .services.adsb_lol import ADSBLolClient
from .services.flight_snapshot import FlightSnapshotService
from .services.opensky import OpenSkyClient


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())
    providers = []

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
    )
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}

    return app
