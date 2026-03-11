from __future__ import annotations

import unittest

from backend.services.aircraft_photos import AircraftPhotoService
from backend.services.openverse import OpenverseClient
from backend.services.provider_base import FlightProviderError
from backend.services.wikimedia_commons import WikimediaCommonsClient


class _ResponseStub:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class _WikimediaCommonsClientStub(WikimediaCommonsClient):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__(
            base_url="https://example.invalid",
            timeout=1,
            max_retries=0,
        )
        self._payload = payload

    def _request_photo_lookup(self, registration: str) -> _ResponseStub:
        return _ResponseStub(self._payload)


class _OpenverseClientStub(OpenverseClient):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__(
            base_url="https://example.invalid",
            timeout=1,
            max_retries=0,
        )
        self._payload = payload

    def _request_photo_lookup(self, registration: str) -> _ResponseStub:
        return _ResponseStub(self._payload)


class _ProviderStub:
    def __init__(
        self,
        photo: dict[str, object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.photo = photo
        self.error = error
        self.calls: list[str | None] = []

    def fetch_photo(self, registration: str | None) -> dict[str, object] | None:
        self.calls.append(registration)
        if self.error:
            raise self.error
        return self.photo


class WikimediaCommonsClientTests(unittest.TestCase):
    def test_fetch_photo_parses_commons_image_result(self) -> None:
        client = _WikimediaCommonsClientStub(
            {
                "query": {
                    "pages": [
                        {
                            "title": "File:American Airlines Boeing 777-200ER N775AN.png",
                            "imageinfo": [
                                {
                                    "user": "Jetstreamer",
                                    "thumburl": "https://upload.wikimedia.org/example-thumb.jpg",
                                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:N775AN",
                                    "extmetadata": {
                                        "Artist": {"value": "Sergey Kustov"},
                                        "LicenseShortName": {"value": "CC BY-SA 3.0"},
                                        "ImageDescription": {
                                            "value": "American Airlines Boeing 777 N775AN departing."
                                        },
                                    },
                                }
                            ],
                        }
                    ]
                }
            }
        )

        photo = client.fetch_photo("N775AN")

        self.assertIsNotNone(photo)
        self.assertEqual(photo["thumbnail_url"], "https://upload.wikimedia.org/example-thumb.jpg")
        self.assertEqual(photo["link"], "https://commons.wikimedia.org/wiki/File:N775AN")
        self.assertEqual(photo["photographer"], "Sergey Kustov")
        self.assertEqual(photo["source"], "Wikimedia Commons")
        self.assertEqual(photo["license"], "CC BY-SA 3.0")

    def test_fetch_photo_prefers_result_with_registration_match(self) -> None:
        client = _WikimediaCommonsClientStub(
            {
                "query": {
                    "pages": [
                        {
                            "title": "File:American Airlines Boeing 777.png",
                            "imageinfo": [
                                {
                                    "user": "Uploader",
                                    "thumburl": "https://upload.wikimedia.org/generic-thumb.jpg",
                                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Generic",
                                    "extmetadata": {},
                                }
                            ],
                        },
                        {
                            "title": "File:American Airlines Boeing 777 N775AN.png",
                            "imageinfo": [
                                {
                                    "user": "Uploader",
                                    "thumburl": "https://upload.wikimedia.org/matched-thumb.jpg",
                                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Matched",
                                    "extmetadata": {},
                                }
                            ],
                        },
                    ]
                }
            }
        )

        photo = client.fetch_photo("N775AN")

        self.assertIsNotNone(photo)
        self.assertEqual(photo["thumbnail_url"], "https://upload.wikimedia.org/matched-thumb.jpg")


class AircraftPhotoServiceTests(unittest.TestCase):
    def test_uses_secondary_provider_when_primary_has_no_photo(self) -> None:
        primary = _ProviderStub(photo=None)
        secondary = _ProviderStub(
            photo={
                "thumbnail_url": "https://example.com/photo.jpg",
                "source": "fallback",
            }
        )
        service = AircraftPhotoService([primary, secondary])

        photo = service.fetch_photo("N775AN")

        self.assertEqual(primary.calls, ["N775AN"])
        self.assertEqual(secondary.calls, ["N775AN"])
        self.assertEqual(photo["source"], "fallback")

    def test_suppresses_primary_error_when_secondary_succeeds(self) -> None:
        primary = _ProviderStub(error=FlightProviderError("Primary unavailable."))
        secondary = _ProviderStub(
            photo={
                "thumbnail_url": "https://example.com/photo.jpg",
                "source": "fallback",
            }
        )
        service = AircraftPhotoService([primary, secondary])

        photo = service.fetch_photo("N775AN")

        self.assertEqual(photo["source"], "fallback")

    def test_raises_when_all_providers_fail(self) -> None:
        service = AircraftPhotoService(
            [
                _ProviderStub(error=FlightProviderError("Primary unavailable.")),
                _ProviderStub(error=FlightProviderError("Fallback unavailable.")),
            ]
        )

        with self.assertRaises(FlightProviderError) as context:
            service.fetch_photo("N775AN")

        self.assertIn("Primary unavailable.", str(context.exception))
        self.assertIn("Fallback unavailable.", str(context.exception))


class OpenverseClientTests(unittest.TestCase):
    def test_fetch_photo_parses_openverse_result(self) -> None:
        client = _OpenverseClientStub(
            {
                "results": [
                    {
                        "title": "N29984",
                        "url": "https://images.example.com/full.jpg",
                        "thumbnail": "https://images.example.com/thumb.jpg",
                        "foreign_landing_url": "https://flickr.example.com/photo",
                        "creator": "gankp",
                        "license": "by-nc-sa",
                        "license_version": "2.0",
                        "provider": "flickr",
                        "attribution": "N29984 by gankp",
                        "fields_matched": ["title", "tags.name"],
                        "tags": [
                            {"name": "n29984"},
                            {"name": "boeing787"},
                        ],
                        "mature": False,
                    }
                ]
            }
        )

        photo = client.fetch_photo("N29984")

        self.assertIsNotNone(photo)
        self.assertEqual(photo["thumbnail_url"], "https://images.example.com/thumb.jpg")
        self.assertEqual(photo["link"], "https://flickr.example.com/photo")
        self.assertEqual(photo["photographer"], "gankp")
        self.assertEqual(photo["source"], "Openverse · flickr")
        self.assertEqual(photo["license"], "BY-NC-SA 2.0")

    def test_fetch_photo_prefers_result_matching_registration_tag(self) -> None:
        client = _OpenverseClientStub(
            {
                "results": [
                    {
                        "title": "United Boeing 787",
                        "url": "https://images.example.com/generic.jpg",
                        "thumbnail": "https://images.example.com/generic-thumb.jpg",
                        "provider": "flickr",
                        "fields_matched": ["title"],
                        "tags": [{"name": "boeing787"}],
                        "mature": False,
                    },
                    {
                        "title": "Dreamliner departure",
                        "url": "https://images.example.com/matched.jpg",
                        "thumbnail": "https://images.example.com/matched-thumb.jpg",
                        "provider": "flickr",
                        "fields_matched": ["tags.name"],
                        "tags": [{"name": "n29984"}],
                        "mature": False,
                    },
                ]
            }
        )

        photo = client.fetch_photo("N29984")

        self.assertIsNotNone(photo)
        self.assertEqual(photo["thumbnail_url"], "https://images.example.com/matched-thumb.jpg")


if __name__ == "__main__":
    unittest.main()
