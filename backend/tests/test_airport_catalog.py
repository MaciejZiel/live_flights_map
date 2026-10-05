from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from backend.services.airport_catalog import AirportCatalogService


CACHED_AIRPORTS_CSV = """id,ident,type,name,latitude_deg,longitude_deg,elevation_ft,continent,iso_country,iso_region,municipality,scheduled_service,gps_code,iata_code,local_code,home_link,wikipedia_link,keywords
1,EPWA,large_airport,Warsaw Chopin Airport,52.1657,20.9671,362,EU,PL,PL-MZ,Warsaw,yes,EPWA,WAW,,,
2,LFPG,large_airport,Charles de Gaulle International Airport,49.0128,2.55,392,EU,FR,FR-IDF,Paris,yes,LFPG,CDG,,,
3,EPMO,medium_airport,Warsaw Modlin Airport,52.4511,20.6518,341,EU,PL,PL-MZ,Nowy Dwor Mazowiecki,no,EPMO,WMI,,,
4,EPLS,small_airport,Strzyzewice Airfield,51.5511,19.1794,620,EU,PL,PL-LD,Strzyzewice,no,EPLS,,,,,
5,PLH1,heliport,Sample Heliport,52.2,21.0,300,EU,PL,PL-MZ,Warsaw,no,PLH1,,,,
"""


class AirportCatalogServiceTests(unittest.TestCase):
    def test_loads_airports_from_cached_catalog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "airports.csv"
            cache_path.write_text(CACHED_AIRPORTS_CSV, encoding="utf-8")

            service = AirportCatalogService(
                airports=(),
                cache_path=str(cache_path),
                cache_ttl=86400,
                catalog_url="",
            )

            airports = service.list_airports_in_bbox(
                bbox={
                    "lamin": 48.0,
                    "lamax": 53.0,
                    "lomin": 2.0,
                    "lomax": 21.5,
                },
                limit=20,
            )

            self.assertEqual(4, len(airports))
            self.assertEqual(["CDG", "WAW", "WMI", "EPLS"], [airport["entity_key"] for airport in airports])

    def test_supports_search_and_code_lookup_with_cached_catalog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "airports.csv"
            cache_path.write_text(CACHED_AIRPORTS_CSV, encoding="utf-8")

            service = AirportCatalogService(
                airports=(),
                cache_path=str(cache_path),
                cache_ttl=86400,
                catalog_url="",
            )

            results = service.search_airports("warsaw", limit=10)
            self.assertEqual(["WAW", "WMI"], [airport["entity_key"] for airport in results[:2]])

            airport_by_iata = service.get_airport("waw")
            airport_by_icao = service.get_airport("lfpg")

            self.assertEqual("Warsaw Chopin Airport", airport_by_iata["name"])
            self.assertEqual("Charles de Gaulle International Airport", airport_by_icao["name"])

    def test_refreshes_remote_catalog_in_background_after_serving_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            started = threading.Event()
            release = threading.Event()
            service = AirportCatalogService(
                airports=(),
                cache_path=str(Path(temp_dir) / "airports.csv"),
                catalog_url="https://example.test/airports.csv",
            )

            def download_catalog():
                started.set()
                release.wait(timeout=2)
                return CACHED_AIRPORTS_CSV

            service._download_catalog = download_catalog
            started_at = time.monotonic()
            self.assertEqual([], service.search_airports("Warsaw", limit=10))
            self.assertLess(time.monotonic() - started_at, 0.5)
            self.assertTrue(started.wait(timeout=1))
            self.assertEqual("refreshing", service.get_catalog_status()["status"])

            release.set()
            self.assertTrue(service._refresh_done.wait(timeout=2))
            self.assertEqual(["WAW", "WMI"], [
                airport["entity_key"]
                for airport in service.search_airports("Warsaw", limit=10)
            ])
            self.assertEqual("remote", service.get_catalog_status()["source"])


if __name__ == "__main__":
    unittest.main()
