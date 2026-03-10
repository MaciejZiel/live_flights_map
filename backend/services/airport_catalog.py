from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians


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


class AirportCatalogService:
    def __init__(
        self,
        airports: tuple[AirportRecord, ...] = MAJOR_AIRPORTS,
        locations: tuple[LocationRecord, ...] = NAMED_LOCATIONS,
    ) -> None:
        self.airports = airports
        self.locations = locations
        self._airport_by_key = {}
        for airport in airports:
            for key in {airport.key, airport.icao or "", airport.iata or ""}:
                normalized = key.strip().upper()
                if normalized:
                    self._airport_by_key[normalized] = airport

    def get_airport(self, code: str | None) -> dict[str, object] | None:
        if not code:
            return None
        airport = self._airport_by_key.get(str(code).strip().upper())
        return airport.to_payload() if airport else None

    def search_airports(self, query: str, limit: int) -> list[dict[str, object]]:
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
