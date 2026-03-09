from flask import Flask

from .config import Config
from .routes import api
from .services.flight_snapshot import FlightSnapshotService
from .services.opensky import OpenSkyClient


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())
    app.extensions["flight_snapshot_service"] = FlightSnapshotService(
        client=OpenSkyClient(
            base_url=app.config["OPENSKY_BASE_URL"],
            username=app.config["OPENSKY_USERNAME"],
            password=app.config["OPENSKY_PASSWORD"],
            timeout=app.config["OPENSKY_TIMEOUT"],
            max_retries=app.config["OPENSKY_RETRY_COUNT"],
        ),
        cache_ttl=app.config["OPENSKY_CACHE_TTL"],
        cooldown_seconds=app.config["OPENSKY_COOLDOWN_SECONDS"],
    )
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}

    return app
