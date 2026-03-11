import os
from tempfile import gettempdir


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


class Config:
    DEBUG = _env_bool("FLASK_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    FLIGHT_ARCHIVE_PATH = os.getenv(
        "FLIGHT_ARCHIVE_PATH",
        os.path.join(gettempdir(), "live-flights-map-history.sqlite3"),
    )
    WORKSPACE_DB_PATH = os.getenv(
        "WORKSPACE_DB_PATH",
        os.path.join(gettempdir(), "live-flights-map-workspace.sqlite3"),
    )
    FLIGHT_ARCHIVE_RETENTION_HOURS = float(
        os.getenv("FLIGHT_ARCHIVE_RETENTION_HOURS", "24")
    )
    FLIGHT_ARCHIVE_MAX_SNAPSHOTS = int(
        os.getenv("FLIGHT_ARCHIVE_MAX_SNAPSHOTS", "720")
    )
    FLIGHT_SEARCH_LOOKBACK_HOURS = float(
        os.getenv("FLIGHT_SEARCH_LOOKBACK_HOURS", "6")
    )
    GLOBAL_TRAFFIC_BOARD_CACHE_TTL = float(
        os.getenv("GLOBAL_TRAFFIC_BOARD_CACHE_TTL", "75")
    )
    GLOBAL_TRAFFIC_BOARD_LOOKBACK_MINUTES = int(
        os.getenv("GLOBAL_TRAFFIC_BOARD_LOOKBACK_MINUTES", "120")
    )
    AIRPORT_WEATHER_BASE_URL = os.getenv(
        "AIRPORT_WEATHER_BASE_URL",
        "https://aviationweather.gov/api/data/metar",
    )
    AIRPORT_WEATHER_TIMEOUT = float(os.getenv("AIRPORT_WEATHER_TIMEOUT", "10"))
    AIRPORT_WEATHER_CACHE_TTL = float(
        os.getenv("AIRPORT_WEATHER_CACHE_TTL", "600")
    )

    OPENSKY_BASE_URL = os.getenv(
        "OPENSKY_BASE_URL",
        "https://opensky-network.org/api/states/all",
    )
    FLIGHT_DATA_PROVIDERS = tuple(
        provider.strip()
        for provider in os.getenv("FLIGHT_DATA_PROVIDERS", "opensky,adsb_lol").split(",")
        if provider.strip()
    )
    OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME")
    OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD")
    OPENSKY_TIMEOUT = float(os.getenv("OPENSKY_TIMEOUT", "10"))
    OPENSKY_RETRY_COUNT = int(os.getenv("OPENSKY_RETRY_COUNT", "1"))
    ADSB_LOL_BASE_URL = os.getenv("ADSB_LOL_BASE_URL", "https://api.adsb.lol")
    ADSB_LOL_TIMEOUT = float(os.getenv("ADSB_LOL_TIMEOUT", "10"))
    ADSB_LOL_RETRY_COUNT = int(os.getenv("ADSB_LOL_RETRY_COUNT", "1"))
    ADSB_LOL_RADIUS_LIMIT_NM = int(os.getenv("ADSB_LOL_RADIUS_LIMIT_NM", "250"))
    ADSB_LOL_ROUTE_API_URL = os.getenv(
        "ADSB_LOL_ROUTE_API_URL",
        "https://api.adsb.lol/api/0/routeset",
    )
    ADSB_LOL_ROUTE_TIMEOUT = float(os.getenv("ADSB_LOL_ROUTE_TIMEOUT", "10"))
    ADSB_LOL_ROUTE_RETRY_COUNT = int(os.getenv("ADSB_LOL_ROUTE_RETRY_COUNT", "1"))
    PLANESPOTTING_BASE_URL = os.getenv(
        "PLANESPOTTING_BASE_URL",
        "https://www.planespotting.be/api/objects/imagesRegistration.php",
    )
    PLANESPOTTING_TIMEOUT = float(os.getenv("PLANESPOTTING_TIMEOUT", "10"))
    PLANESPOTTING_RETRY_COUNT = int(os.getenv("PLANESPOTTING_RETRY_COUNT", "1"))
    WIKIMEDIA_COMMONS_BASE_URL = os.getenv(
        "WIKIMEDIA_COMMONS_BASE_URL",
        "https://commons.wikimedia.org/w/api.php",
    )
    WIKIMEDIA_COMMONS_TIMEOUT = float(os.getenv("WIKIMEDIA_COMMONS_TIMEOUT", "10"))
    WIKIMEDIA_COMMONS_RETRY_COUNT = int(os.getenv("WIKIMEDIA_COMMONS_RETRY_COUNT", "1"))
    OPENVERSE_BASE_URL = os.getenv(
        "OPENVERSE_BASE_URL",
        "https://api.openverse.org/v1/images/",
    )
    OPENVERSE_TIMEOUT = float(os.getenv("OPENVERSE_TIMEOUT", "10"))
    OPENVERSE_RETRY_COUNT = int(os.getenv("OPENVERSE_RETRY_COUNT", "1"))
    AIRCRAFT_PHOTO_PROXY_TIMEOUT = float(
        os.getenv("AIRCRAFT_PHOTO_PROXY_TIMEOUT", "12")
    )
    AIRCRAFT_PHOTO_PROXY_ALLOWED_HOSTS = tuple(
        host.strip().lower()
        for host in os.getenv(
            "AIRCRAFT_PHOTO_PROXY_ALLOWED_HOSTS",
            ",".join(
                (
                    "planespotting.be",
                    "www.planespotting.be",
                    "upload.wikimedia.org",
                    "commons.wikimedia.org",
                    "staticflickr.com",
                    "live.staticflickr.com",
                    "flickr.com",
                    "farm.staticflickr.com",
                )
            ),
        ).split(",")
        if host.strip()
    )
    AIRCRAFT_PHOTO_CACHE_PATH = os.getenv(
        "AIRCRAFT_PHOTO_CACHE_PATH",
        os.path.join(gettempdir(), "live-flights-map-aircraft-photo-cache.sqlite3"),
    )
    AIRCRAFT_PHOTO_LOOKUP_CACHE_TTL = float(
        os.getenv("AIRCRAFT_PHOTO_LOOKUP_CACHE_TTL", "86400")
    )
    AIRCRAFT_PHOTO_ASSET_CACHE_TTL = float(
        os.getenv("AIRCRAFT_PHOTO_ASSET_CACHE_TTL", "86400")
    )
    OPENSKY_CACHE_TTL = float(os.getenv("OPENSKY_CACHE_TTL", "25"))
    OPENSKY_COOLDOWN_SECONDS = float(os.getenv("OPENSKY_COOLDOWN_SECONDS", "75"))
    OPENSKY_CACHE_PATH = os.getenv(
        "OPENSKY_CACHE_PATH",
        os.path.join(gettempdir(), "live-flights-map-opensky-cache.json"),
    )
    LIVE_LATEST_CACHE_MAX_AGE_SECONDS = float(
        os.getenv("LIVE_LATEST_CACHE_MAX_AGE_SECONDS", "150")
    )
    FLIGHT_DETAILS_CACHE_TTL = float(os.getenv("FLIGHT_DETAILS_CACHE_TTL", "21600"))
    FLIGHT_STREAM_INTERVAL_SECONDS = float(
        os.getenv("FLIGHT_STREAM_INTERVAL_SECONDS", "30")
    )

    MAP_DEFAULT_LAMIN = float(os.getenv("MAP_DEFAULT_LAMIN", "49.0"))
    MAP_DEFAULT_LAMAX = float(os.getenv("MAP_DEFAULT_LAMAX", "55.1"))
    MAP_DEFAULT_LOMIN = float(os.getenv("MAP_DEFAULT_LOMIN", "14.0"))
    MAP_DEFAULT_LOMAX = float(os.getenv("MAP_DEFAULT_LOMAX", "24.5"))

    CORS_ALLOWED_ORIGIN = os.getenv("CORS_ALLOWED_ORIGIN", "*")
