from flask import Flask

from .config import Config
from .routes import api


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}

    return app
