import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


class Config:
    DEBUG = _env_bool("FLASK_DEBUG", False)
    PORT = int(os.getenv("PORT", "5000"))

    OPENSKY_BASE_URL = os.getenv(
        "OPENSKY_BASE_URL",
        "https://opensky-network.org/api/states/all",
    )
    OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME")
    OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD")
    OPENSKY_TIMEOUT = float(os.getenv("OPENSKY_TIMEOUT", "10"))

    MAP_DEFAULT_LAMIN = float(os.getenv("MAP_DEFAULT_LAMIN", "49.0"))
    MAP_DEFAULT_LAMAX = float(os.getenv("MAP_DEFAULT_LAMAX", "55.1"))
    MAP_DEFAULT_LOMIN = float(os.getenv("MAP_DEFAULT_LOMIN", "14.0"))
    MAP_DEFAULT_LOMAX = float(os.getenv("MAP_DEFAULT_LOMAX", "24.5"))

    CORS_ALLOWED_ORIGIN = os.getenv("CORS_ALLOWED_ORIGIN", "*")
