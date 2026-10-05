from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from math import cos, radians
from pathlib import Path
from tempfile import gettempdir
from threading import Event, Lock, Thread
from time import time

import requests


@dataclass(frozen=True, slots=True)
class AirportRecord:
    key: str
    icao: str | None
    iata: str | None
    name: str
    city: str
    country: str
    latitude: float
    longitude: float
    importance: int
    airport_type: str = "airport"

    @property
    def label(self) -> str:
        return self.iata or self.icao or self.city

    @property
    def search_blob(self) -> str:
        return " ".join(
            part.lower()
            for part in (
                self.key,
                self.icao or "",
                self.iata or "",
                self.name,
                self.city,
                self.country,
            )
            if part
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "entity_type": "airport",
            "entity_key": self.key,
            "icao": self.icao,
            "iata": self.iata,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "importance": self.importance,
            "airport_type": self.airport_type,
            "label": self.label,
            "subtitle": f"{self.city}, {self.country}",
        }


@dataclass(frozen=True, slots=True)
class LocationRecord:
    key: str
    label: str
    subtitle: str
    center: tuple[float, float]
    zoom: float
    bbox: dict[str, float]

    @property
    def search_blob(self) -> str:
        return f"{self.key} {self.label} {self.subtitle}".lower()

    def to_payload(self) -> dict[str, object]:
        return {
            "entity_type": "location",
            "entity_key": self.key,
            "label": self.label,
            "subtitle": self.subtitle,
            "latitude": self.center[0],
            "longitude": self.center[1],
            "zoom": self.zoom,
            "bbox": self.bbox,
        }


def _airport(
    icao: str,
    iata: str,
    name: str,
    city: str,
    country: str,
    latitude: float,
    longitude: float,
    importance: int,
    airport_type: str = "airport",
) -> AirportRecord:
    return AirportRecord(
        key=(iata or icao).upper(),
        icao=icao.upper() if icao else None,
        iata=iata.upper() if iata else None,
        name=name,
        city=city,
        country=country,
        latitude=latitude,
        longitude=longitude,
        importance=importance,
        airport_type=airport_type,
    )


MAJOR_AIRPORTS: tuple[AirportRecord, ...] = (
    _airport("EPWA", "WAW", "Warsaw Chopin Airport", "Warsaw", "Poland", 52.1657, 20.9671, 10),
    _airport("EPKK", "KRK", "Krakow John Paul II Airport", "Krakow", "Poland", 50.0777, 19.7848, 7),
    _airport("EGLL", "LHR", "Heathrow Airport", "London", "United Kingdom", 51.4700, -0.4543, 10),
    _airport("EGKK", "LGW", "Gatwick Airport", "London", "United Kingdom", 51.1537, -0.1821, 8),
    _airport("LFPG", "CDG", "Charles de Gaulle Airport", "Paris", "France", 49.0097, 2.5479, 10),
    _airport("LFPO", "ORY", "Paris Orly Airport", "Paris", "France", 48.7262, 2.3652, 7),
    _airport("EHAM", "AMS", "Amsterdam Airport Schiphol", "Amsterdam", "Netherlands", 52.3105, 4.7683, 10),
    _airport("EDDF", "FRA", "Frankfurt Airport", "Frankfurt", "Germany", 50.0379, 8.5622, 10),
    _airport("EDDM", "MUC", "Munich Airport", "Munich", "Germany", 48.3538, 11.7861, 8),
    _airport("LEMD", "MAD", "Adolfo Suarez Madrid-Barajas Airport", "Madrid", "Spain", 40.4983, -3.5676, 9),
    _airport("LEBL", "BCN", "Barcelona El Prat Airport", "Barcelona", "Spain", 41.2974, 2.0833, 8),
    _airport("LIRF", "FCO", "Rome Fiumicino Airport", "Rome", "Italy", 41.8003, 12.2389, 8),
    _airport("LOWW", "VIE", "Vienna International Airport", "Vienna", "Austria", 48.1103, 16.5697, 7),
    _airport("LSZH", "ZRH", "Zurich Airport", "Zurich", "Switzerland", 47.4582, 8.5555, 7),
    _airport("LTFM", "IST", "Istanbul Airport", "Istanbul", "Turkey", 41.2753, 28.7519, 9),
    _airport("UUEE", "SVO", "Sheremetyevo International Airport", "Moscow", "Russia", 55.9726, 37.4146, 7),
    _airport("OTHH", "DOH", "Hamad International Airport", "Doha", "Qatar", 25.2731, 51.6081, 9),
    _airport("OMDB", "DXB", "Dubai International Airport", "Dubai", "United Arab Emirates", 25.2532, 55.3657, 10),
    _airport("OMAA", "AUH", "Zayed International Airport", "Abu Dhabi", "United Arab Emirates", 24.4330, 54.6511, 7),
    _airport("OERK", "RUH", "King Khalid International Airport", "Riyadh", "Saudi Arabia", 24.9576, 46.6988, 7),
    _airport("HECA", "CAI", "Cairo International Airport", "Cairo", "Egypt", 30.1219, 31.4056, 7),
    _airport("FAOR", "JNB", "O. R. Tambo International Airport", "Johannesburg", "South Africa", -26.1337, 28.2420, 8),
    _airport("HKJK", "NBO", "Jomo Kenyatta International Airport", "Nairobi", "Kenya", -1.3192, 36.9278, 6),
    _airport("DNMM", "LOS", "Murtala Muhammed International Airport", "Lagos", "Nigeria", 6.5774, 3.3212, 6),
    _airport("GMMN", "CMN", "Mohammed V International Airport", "Casablanca", "Morocco", 33.3675, -7.5899, 6),
    _airport("KJFK", "JFK", "John F. Kennedy International Airport", "New York", "United States", 40.6413, -73.7781, 10),
    _airport("KEWR", "EWR", "Newark Liberty International Airport", "Newark", "United States", 40.6895, -74.1745, 8),
    _airport("KLAX", "LAX", "Los Angeles International Airport", "Los Angeles", "United States", 33.9416, -118.4085, 10),
    _airport("KSFO", "SFO", "San Francisco International Airport", "San Francisco", "United States", 37.6213, -122.3790, 8),
    _airport("KORD", "ORD", "Chicago O'Hare International Airport", "Chicago", "United States", 41.9742, -87.9073, 9),
    _airport("KATL", "ATL", "Hartsfield-Jackson Atlanta International Airport", "Atlanta", "United States", 33.6407, -84.4277, 10),
    _airport("KDFW", "DFW", "Dallas Fort Worth International Airport", "Dallas", "United States", 32.8998, -97.0403, 8),
    _airport("KDEN", "DEN", "Denver International Airport", "Denver", "United States", 39.8561, -104.6737, 8),
    _airport("KMIA", "MIA", "Miami International Airport", "Miami", "United States", 25.7959, -80.2870, 8),
    _airport("KIAD", "IAD", "Washington Dulles International Airport", "Washington", "United States", 38.9531, -77.4565, 7),
    _airport("KSEA", "SEA", "Seattle-Tacoma International Airport", "Seattle", "United States", 47.4502, -122.3088, 7),
    _airport("CYYZ", "YYZ", "Toronto Pearson International Airport", "Toronto", "Canada", 43.6777, -79.6248, 8),
    _airport("CYVR", "YVR", "Vancouver International Airport", "Vancouver", "Canada", 49.1967, -123.1815, 7),
    _airport("MMMX", "MEX", "Mexico City International Airport", "Mexico City", "Mexico", 19.4361, -99.0719, 7),
    _airport("SBGR", "GRU", "Sao Paulo Guarulhos International Airport", "Sao Paulo", "Brazil", -23.4356, -46.4731, 8),
    _airport("SAEZ", "EZE", "Ministro Pistarini International Airport", "Buenos Aires", "Argentina", -34.8222, -58.5358, 7),
    _airport("SCEL", "SCL", "Arturo Merino Benitez Airport", "Santiago", "Chile", -33.3929, -70.7858, 6),
    _airport("SKBO", "BOG", "El Dorado International Airport", "Bogota", "Colombia", 4.7016, -74.1469, 6),
    _airport("RJTT", "HND", "Tokyo Haneda Airport", "Tokyo", "Japan", 35.5494, 139.7798, 10),
    _airport("RJAA", "NRT", "Narita International Airport", "Tokyo", "Japan", 35.7720, 140.3929, 8),
    _airport("RKSI", "ICN", "Incheon International Airport", "Seoul", "South Korea", 37.4602, 126.4407, 9),
    _airport("ZBAA", "PEK", "Beijing Capital International Airport", "Beijing", "China", 40.0799, 116.6031, 9),
    _airport("ZSPD", "PVG", "Shanghai Pudong International Airport", "Shanghai", "China", 31.1443, 121.8083, 9),
    _airport("VHHH", "HKG", "Hong Kong International Airport", "Hong Kong", "China", 22.3080, 113.9185, 9),
    _airport("WSSS", "SIN", "Singapore Changi Airport", "Singapore", "Singapore", 1.3644, 103.9915, 10),
    _airport("VTBS", "BKK", "Suvarnabhumi Airport", "Bangkok", "Thailand", 13.6900, 100.7501, 8),
    _airport("WMKK", "KUL", "Kuala Lumpur International Airport", "Kuala Lumpur", "Malaysia", 2.7456, 101.7099, 7),
    _airport("VIDP", "DEL", "Indira Gandhi International Airport", "Delhi", "India", 28.5562, 77.1000, 9),
    _airport("VABB", "BOM", "Chhatrapati Shivaji Maharaj International Airport", "Mumbai", "India", 19.0896, 72.8656, 8),
    _airport("YSSY", "SYD", "Sydney Kingsford Smith Airport", "Sydney", "Australia", -33.9399, 151.1753, 9),
    _airport("YMML", "MEL", "Melbourne Airport", "Melbourne", "Australia", -37.6690, 144.8410, 7),
    _airport("NZAA", "AKL", "Auckland Airport", "Auckland", "New Zealand", -37.0082, 174.7850, 7),
    _airport("RPLL", "MNL", "Ninoy Aquino International Airport", "Manila", "Philippines", 14.5086, 121.0198, 7),
)

NAMED_LOCATIONS: tuple[LocationRecord, ...] = (
    LocationRecord(
        key="poland",
        label="Poland",
        subtitle="National airspace focus",
        center=(52.15, 19.40),
        zoom=6.8,
        bbox={"lamin": 49.0, "lamax": 55.1, "lomin": 14.0, "lomax": 24.5},
    ),
    LocationRecord(
        key="europe",
        label="Europe",
        subtitle="Mainland Europe and nearby traffic",
        center=(51.0, 10.0),
        zoom=4.3,
        bbox={"lamin": 35.0, "lamax": 71.0, "lomin": -11.0, "lomax": 35.0},
    ),
    LocationRecord(
        key="north-atlantic",
        label="North Atlantic",
        subtitle="Transatlantic traffic lanes",
        center=(52.0, -30.0),
        zoom=3.6,
        bbox={"lamin": 35.0, "lamax": 64.0, "lomin": -70.0, "lomax": 10.0},
    ),
    LocationRecord(
        key="east-coast-usa",
        label="US East Coast",
        subtitle="New York, Washington and Atlantic corridor",
        center=(39.9, -75.2),
        zoom=5.2,
        bbox={"lamin": 31.0, "lamax": 46.0, "lomin": -82.0, "lomax": -67.0},
    ),
    LocationRecord(
        key="west-coast-usa",
        label="US West Coast",
        subtitle="California and Pacific gateway traffic",
        center=(36.8, -121.0),
        zoom=5.2,
        bbox={"lamin": 30.0, "lamax": 49.0, "lomin": -128.0, "lomax": -110.0},
    ),
    LocationRecord(
        key="middle-east",
        label="Middle East",
        subtitle="Gulf hubs and regional traffic",
        center=(25.2, 52.0),
        zoom=5.0,
        bbox={"lamin": 12.0, "lamax": 38.0, "lomin": 34.0, "lomax": 60.0},
    ),
    LocationRecord(
        key="east-asia",
        label="East Asia",
        subtitle="Japan, Korea, China and nearby traffic",
        center=(33.8, 127.0),
        zoom=4.5,
        bbox={"lamin": 18.0, "lamax": 48.0, "lomin": 104.0, "lomax": 145.0},
    ),
    LocationRecord(
        key="southeast-asia",
        label="Southeast Asia",
        subtitle="Singapore, Bangkok, Kuala Lumpur and Manila",
        center=(10.0, 107.0),
        zoom=4.7,
        bbox={"lamin": -4.0, "lamax": 23.0, "lomin": 94.0, "lomax": 123.0},
    ),
    LocationRecord(
        key="oceania",
        label="Oceania",
        subtitle="Australia and New Zealand trunk traffic",
        center=(-31.0, 151.0),
        zoom=4.4,
        bbox={"lamin": -48.0, "lamax": -10.0, "lomin": 110.0, "lomax": 179.0},
    ),
    LocationRecord(
        key="south-america",
        label="South America",
        subtitle="Brazil, Andes and southern cone traffic",
        center=(-22.0, -59.0),
        zoom=4.2,
        bbox={"lamin": -56.0, "lamax": 12.0, "lomin": -84.0, "lomax": -34.0},
    ),
)

REMOTE_AIRPORT_IMPORTANCE = {
    "large_airport": 10,
    "medium_airport": 8,
    "small_airport": 4,
    "seaplane_base": 3,
    "balloonport": 2,
}


class AirportCatalogService:
    def __init__(
        self,
        airports: tuple[AirportRecord, ...] = MAJOR_AIRPORTS,
        locations: tuple[LocationRecord, ...] = NAMED_LOCATIONS,
        catalog_url: str | None = None,
        cache_path: str | None = None,
        cache_ttl: float = 86400.0,
        timeout: float = 20.0,
    ) -> None:
        self._fallback_airports = tuple(airports)
        self.locations = locations
        self.catalog_url = str(catalog_url or "").strip()
        self.cache_path = (
            Path(cache_path).expanduser()
            if cache_path
            else Path(gettempdir()) / "live-flights-map-airports.csv"
        )
        self.cache_ttl = max(float(cache_ttl or 0), 3600.0)
        self.timeout = max(float(timeout or 0), 1.0)
        self.session = requests.Session()
        self._lock = Lock()
        self._catalog_loaded = False
        self._refresh_started = False
        self._refreshing = False
        self._refresh_thread: Thread | None = None
        self._refresh_done = Event()
        self._catalog_source = "bundled"
        self._catalog_error: str | None = None
        self._catalog_updated_at: str | None = None
        self.airports = self._fallback_airports
        self._airport_by_key: dict[str, AirportRecord] = {}
        self._rebuild_indexes(self.airports)

    def get_airport(self, code: str | None) -> dict[str, object] | None:
        self._ensure_catalog_loaded()
        if not code:
            return None
        airport = self._airport_by_key.get(str(code).strip().upper())
        return airport.to_payload() if airport else None

    def get_catalog_status(self) -> dict[str, object]:
        self._ensure_catalog_loaded()
        return {
            "status": "refreshing" if self._refreshing else (
                "degraded" if self._catalog_error else "ready"
            ),
            "source": self._catalog_source,
            "updated_at": self._catalog_updated_at,
            "warning": self._catalog_error,
        }

    def search_airports(self, query: str, limit: int) -> list[dict[str, object]]:
        self._ensure_catalog_loaded()
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        def score(record: AirportRecord) -> tuple[int, int]:
            exact_code = int(
                normalized_query
                in {
                    (record.iata or "").lower(),
                    (record.icao or "").lower(),
                    record.key.lower(),
                }
            )
            startswith = int(record.search_blob.startswith(normalized_query))
            return (exact_code * 100 + startswith * 10 + record.importance, record.importance)

        matches = [
            airport
            for airport in self.airports
            if normalized_query in airport.search_blob
        ]
        matches.sort(key=score, reverse=True)
        return [airport.to_payload() for airport in matches[: max(limit, 1)]]

    def search_locations(self, query: str, limit: int) -> list[dict[str, object]]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        matches = [
            location
            for location in self.locations
            if normalized_query in location.search_blob
        ]
        matches.sort(
            key=lambda location: (
                int(location.label.lower().startswith(normalized_query)),
                len(location.label),
            ),
            reverse=True,
        )
        return [location.to_payload() for location in matches[: max(limit, 1)]]

    def list_airports_in_bbox(
        self,
        bbox: dict[str, float] | None,
        limit: int,
    ) -> list[dict[str, object]]:
        self._ensure_catalog_loaded()
        if not bbox:
            return []

        matches = [
            airport
            for airport in self.airports
            if bbox["lamin"] <= airport.latitude <= bbox["lamax"]
            and bbox["lomin"] <= airport.longitude <= bbox["lomax"]
        ]
        matches.sort(key=lambda airport: airport.importance, reverse=True)
        return [airport.to_payload() for airport in matches[: max(limit, 1)]]

    def list_nearby_airports(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        limit: int,
    ) -> list[dict[str, object]]:
        radius_lat = radius_km / 111.0
        radius_lon = radius_km / max(30.0, 111.0 * cos(radians(latitude)))
        bbox = {
            "lamin": latitude - radius_lat,
            "lamax": latitude + radius_lat,
            "lomin": longitude - radius_lon,
            "lomax": longitude + radius_lon,
        }
        return self.list_airports_in_bbox(bbox=bbox, limit=limit)

    def _rebuild_indexes(self, airports: tuple[AirportRecord, ...]) -> None:
        next_index: dict[str, AirportRecord] = {}
        for airport in airports:
            for key in {airport.key, airport.icao or "", airport.iata or ""}:
                normalized = key.strip().upper()
                if not normalized:
                    continue
                current = next_index.get(normalized)
                if current is None or airport.importance > current.importance:
                    next_index[normalized] = airport
        self._airport_by_key = next_index

    def _ensure_catalog_loaded(self) -> None:
        if self._catalog_loaded:
            return

        with self._lock:
            if self._catalog_loaded:
                return

            airports = self._load_cached_airports(require_fresh=True)
            if airports:
                self.airports = airports
                self._rebuild_indexes(airports)
                self._catalog_source = "cache"
                self._catalog_updated_at = self._cache_updated_at()
                self._catalog_loaded = True
                return

            airports = self._load_cached_airports(require_fresh=False)
            if airports:
                self.airports = airports
                self._rebuild_indexes(airports)
                self._catalog_source = "stale_cache"
                self._catalog_updated_at = self._cache_updated_at()

            self._catalog_loaded = True
            if self.catalog_url and not self._refresh_started:
                self._refresh_started = True
                self._refreshing = True
                self._refresh_thread = Thread(
                    target=self._refresh_catalog,
                    daemon=True,
                    name="airport-catalog-refresh",
                )
                self._refresh_thread.start()

    def _refresh_catalog(self) -> None:
        try:
            payload = self._download_catalog()
            airports = self._parse_catalog(payload or "")
            if not airports:
                raise ValueError("The airport catalog did not contain usable airport records.")
            self._store_cached_catalog(payload or "")
            with self._lock:
                self.airports = airports
                self._rebuild_indexes(airports)
                self._catalog_source = "remote"
                self._catalog_updated_at = datetime.now(timezone.utc).isoformat()
                self._catalog_error = None
        except (ValueError, requests.RequestException):
            with self._lock:
                self._catalog_error = "Airport catalog refresh failed; using the last available catalog."
        finally:
            with self._lock:
                self._refreshing = False
                self._refresh_done.set()

    def _cache_updated_at(self) -> str | None:
        try:
            return datetime.fromtimestamp(
                self.cache_path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
        except OSError:
            return None

    def _load_cached_airports(
        self,
        *,
        require_fresh: bool,
    ) -> tuple[AirportRecord, ...] | None:
        if not self.cache_path.exists():
            return None

        try:
            if require_fresh and not self._cache_is_fresh():
                return None
            payload = self.cache_path.read_text(encoding="utf-8")
        except OSError:
            return None

        airports = self._parse_catalog(payload)
        return airports or None

    def _cache_is_fresh(self) -> bool:
        try:
            cache_age_seconds = max(0.0, time() - self.cache_path.stat().st_mtime)
        except OSError:
            return False
        return cache_age_seconds <= self.cache_ttl

    def _download_catalog(self) -> str | None:
        if not self.catalog_url:
            return None

        try:
            response = self.session.get(self.catalog_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException:
            return None

        return response.text

    def _store_cached_catalog(self, payload: str) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(payload, encoding="utf-8")
        except OSError:
            return

    def _parse_catalog(self, payload: str) -> tuple[AirportRecord, ...]:
        airports_by_key: dict[str, AirportRecord] = {}

        for row in csv.DictReader(payload.splitlines()):
            airport = self._build_remote_airport(row)
            if airport is None:
                continue

            existing = airports_by_key.get(airport.key)
            if existing is None or self._airport_rank(airport) > self._airport_rank(existing):
                airports_by_key[airport.key] = airport

        return tuple(
            sorted(
                airports_by_key.values(),
                key=lambda airport: (
                    -airport.importance,
                    airport.country,
                    airport.city,
                    airport.name,
                ),
            )
        )

    def _build_remote_airport(self, row: dict[str, str]) -> AirportRecord | None:
        airport_type = self._normalize_text(row.get("type"), uppercase=False)
        if airport_type not in REMOTE_AIRPORT_IMPORTANCE:
            return None

        latitude = self._parse_float(row.get("latitude_deg"))
        longitude = self._parse_float(row.get("longitude_deg"))
        if latitude is None or longitude is None:
            return None

        name = self._normalize_text(row.get("name"))
        if not name:
            return None

        iata = self._normalize_code(row.get("iata_code"))
        icao = self._normalize_code(row.get("gps_code")) or self._normalize_code(
            row.get("ident")
        )
        key = iata or icao
        if not key:
            return None

        municipality = self._normalize_text(row.get("municipality")) or name
        country = self._normalize_text(row.get("iso_country"), uppercase=True) or "N/A"
        scheduled_service = self._normalize_text(
            row.get("scheduled_service"),
            uppercase=False,
        )

        importance = REMOTE_AIRPORT_IMPORTANCE[airport_type]
        if scheduled_service == "yes":
            importance += 2
        if iata:
            importance += 1
        if icao and len(icao) == 4:
            importance += 1

        return AirportRecord(
            key=key,
            icao=icao,
            iata=iata,
            name=name,
            city=municipality,
            country=country,
            latitude=latitude,
            longitude=longitude,
            importance=importance,
            airport_type=airport_type,
        )

    @staticmethod
    def _airport_rank(airport: AirportRecord) -> tuple[int, int, int, int]:
        return (
            airport.importance,
            int(bool(airport.iata)),
            int(bool(airport.icao)),
            len(airport.name),
        )

    @staticmethod
    def _parse_float(value: object) -> float | None:
        if value in {None, ""}:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return normalized.upper() if uppercase else normalized

    @classmethod
    def _normalize_code(cls, value: object) -> str | None:
        return cls._normalize_text(value, uppercase=True)
