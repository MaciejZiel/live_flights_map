from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend import create_app
from backend.config import Config
from backend.services.alert_delivery import AlertDeliveryError, AlertDeliveryService


class AlertDeliveryServiceTests(unittest.TestCase):
    def test_rejects_invalid_webhook_scheme(self) -> None:
        service = AlertDeliveryService(timeout=5, allowed_schemes=("https",))

        with self.assertRaises(AlertDeliveryError):
            service.deliver_webhook("ftp://example.com/hook", {"message": "test"})

    def test_posts_json_payload_to_webhook(self) -> None:
        service = AlertDeliveryService(timeout=5, allowed_schemes=("https",))
        response = Mock(status_code=202)
        response.raise_for_status.return_value = None

        with patch.object(service.session, "post", return_value=response) as post_mock:
            result = service.deliver_webhook("https://example.com/hook", {"message": "test"})

        self.assertEqual(result.status_code, 202)
        post_mock.assert_called_once()


class AlertDeliveryRouteTests(unittest.TestCase):
    def test_api_route_proxies_webhook_delivery(self) -> None:
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

            response = Mock(status_code=200)
            response.raise_for_status.return_value = None
            with patch.object(
                app.extensions["alert_delivery_service"].session,
                "post",
                return_value=response,
            ):
                payload = client.post(
                    "/api/alerts/deliver",
                    json={
                        "url": "https://example.com/hook",
                        "event": {"message": "Alert fired"},
                    },
                )

        self.assertEqual(payload.status_code, 200)
        self.assertEqual(payload.get_json()["status"], "delivered")


if __name__ == "__main__":
    unittest.main()
