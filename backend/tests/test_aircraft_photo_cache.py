from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.aircraft_photo_cache import AircraftPhotoCacheService


class AircraftPhotoCacheServiceTests(unittest.TestCase):
    def test_stores_and_loads_lookup_and_asset_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AircraftPhotoCacheService(
                str(Path(temp_dir) / "aircraft-photo-cache.sqlite3")
            )

            service.store_lookup(
                "lookup:n775an",
                {
                    "thumbnail_url": "https://example.com/thumb.jpg",
                    "source": "Wikimedia Commons",
                },
                ttl_seconds=3600,
            )
            service.store_asset(
                "https://example.com/thumb.jpg",
                body=b"image-bytes",
                content_type="image/jpeg",
                etag='"etag-demo"',
                ttl_seconds=3600,
            )

            lookup = service.get_lookup("lookup:n775an")
            asset = service.get_asset("https://example.com/thumb.jpg")
            summary = service.summarize()

            self.assertEqual(lookup["thumbnail_url"], "https://example.com/thumb.jpg")
            self.assertEqual(asset["body"], b"image-bytes")
            self.assertEqual(asset["content_type"], "image/jpeg")
            self.assertTrue(summary["available"])
            self.assertEqual(summary["lookup_rows"], 1)
            self.assertEqual(summary["asset_rows"], 1)


if __name__ == "__main__":
    unittest.main()
