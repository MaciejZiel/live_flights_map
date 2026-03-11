from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import create_app
from backend.config import Config
from backend.services.aircraft_photo_cache import AircraftPhotoCacheService
from backend.services.aircraft_photo_proxy import (
    AircraftPhotoAsset,
    AircraftPhotoProxyError,
    AircraftPhotoProxyService,
)


class AircraftPhotoProxyServiceTests(unittest.TestCase):
    def test_rejects_unapproved_host(self) -> None:
        service = AircraftPhotoProxyService(
            timeout=10,
            allowed_hosts=("planespotting.be", "upload.wikimedia.org"),
        )

        with self.assertRaises(AircraftPhotoProxyError):
            service.fetch_asset("https://example.com/photo.jpg")

    def test_reuses_cached_asset_without_second_network_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_service = AircraftPhotoCacheService(
                str(Path(temp_dir) / "photo-cache.sqlite3")
            )
            service = AircraftPhotoProxyService(
                timeout=10,
                allowed_hosts=("planespotting.be", "upload.wikimedia.org"),
                cache_service=cache_service,
                cache_ttl_seconds=3600,
            )

            class _ResponseStub:
                content = b"image-bytes"
                headers = {"Content-Type": "image/jpeg", "ETag": '"etag-demo"'}

                @staticmethod
                def raise_for_status() -> None:
                    return None

            with patch.object(service.session, "get", return_value=_ResponseStub()) as session_get:
                first = service.fetch_asset("https://upload.wikimedia.org/demo.jpg")
                second = service.fetch_asset("https://upload.wikimedia.org/demo.jpg")

            self.assertEqual(first.body, b"image-bytes")
            self.assertEqual(second.body, b"image-bytes")
            session_get.assert_called_once()


class AircraftPhotoProxyRouteTests(unittest.TestCase):
    def test_proxy_route_streams_image_from_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = str(Path(temp_dir) / "history.sqlite3")
            workspace_path = str(Path(temp_dir) / "workspace.sqlite3")
            cache_path = str(Path(temp_dir) / "snapshot-cache.json")
            photo_cache_path = str(Path(temp_dir) / "photo-cache.sqlite3")
            with patch.multiple(
                Config,
                FLIGHT_ARCHIVE_PATH=archive_path,
                WORKSPACE_DB_PATH=workspace_path,
                OPENSKY_CACHE_PATH=cache_path,
                AIRCRAFT_PHOTO_CACHE_PATH=photo_cache_path,
                FLIGHT_DATA_PROVIDERS=("adsb_lol",),
            ):
                app = create_app()
                client = app.test_client()

            proxy_service = app.extensions["aircraft_photo_proxy_service"]
            with patch.object(
                proxy_service,
                "fetch_asset",
                return_value=AircraftPhotoAsset(
                    body=b"fake-image",
                    content_type="image/webp",
                    etag='"demo-etag"',
                ),
            ) as fetch_asset:
                response = client.get(
                    "/api/aircraft-photo",
                    query_string={
                        "url": "https://www.planespotting.be/uploads/example-thumb.jpg"
                    },
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "image/webp")
            self.assertEqual(response.data, b"fake-image")
            self.assertEqual(response.headers["ETag"], '"demo-etag"')
            fetch_asset.assert_called_once()

    def test_proxy_route_validates_missing_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = str(Path(temp_dir) / "history.sqlite3")
            workspace_path = str(Path(temp_dir) / "workspace.sqlite3")
            cache_path = str(Path(temp_dir) / "snapshot-cache.json")
            photo_cache_path = str(Path(temp_dir) / "photo-cache.sqlite3")
            with patch.multiple(
                Config,
                FLIGHT_ARCHIVE_PATH=archive_path,
                WORKSPACE_DB_PATH=workspace_path,
                OPENSKY_CACHE_PATH=cache_path,
                AIRCRAFT_PHOTO_CACHE_PATH=photo_cache_path,
                FLIGHT_DATA_PROVIDERS=("adsb_lol",),
            ):
                app = create_app()
                client = app.test_client()

            response = client.get("/api/aircraft-photo")

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json()["error"], "Missing 'url' query parameter.")


if __name__ == "__main__":
    unittest.main()
