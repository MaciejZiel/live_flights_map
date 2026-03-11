from __future__ import annotations

from html import unescape
from re import sub
from typing import Any

import requests

from .provider_base import FlightProviderError, FlightProviderRateLimitError


class WikimediaCommonsError(FlightProviderError):
    pass


class WikimediaCommonsRateLimitError(FlightProviderRateLimitError, WikimediaCommonsError):
    pass


class WikimediaCommonsClient:
    name = "wikimedia_commons"

    def __init__(self, base_url: str, timeout: float, max_retries: int) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max(max_retries, 0)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "live-flights-map/0.1 (Wikimedia Commons aircraft photo lookup)",
            }
        )

    def fetch_photo(self, registration: str | None) -> dict[str, Any] | None:
        normalized_registration = self._normalize_text(registration, uppercase=True)
        if not normalized_registration:
            return None

        response = self._request_photo_lookup(normalized_registration)
        payload = response.json()
        pages = payload.get("query", {}).get("pages") or []
        if not isinstance(pages, list) or not pages:
            return None

        normalized_pages = sorted(
            (
                self._normalize_page(page, normalized_registration)
                for page in pages
                if isinstance(page, dict)
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        normalized_pages = [page for page in normalized_pages if page["photo"]]
        if not normalized_pages:
            return None

        return normalized_pages[0]["photo"]

    def _request_photo_lookup(self, registration: str) -> requests.Response:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": registration,
            "gsrnamespace": 6,
            "gsrlimit": 5,
            "prop": "imageinfo|info",
            "iiprop": "url|user|extmetadata",
            "iiurlwidth": 960,
            "format": "json",
            "formatversion": 2,
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response
            except requests.Timeout as exc:
                if attempt < self.max_retries:
                    continue
                raise WikimediaCommonsError("Wikimedia Commons photo lookup timed out.") from exc
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code == 429:
                    raise WikimediaCommonsRateLimitError(
                        "Wikimedia Commons photo lookup rate limited."
                    ) from exc
                raise WikimediaCommonsError(
                    f"Wikimedia Commons photo lookup returned HTTP {status_code}."
                ) from exc
            except requests.ConnectionError as exc:
                if attempt < self.max_retries:
                    continue
                raise WikimediaCommonsError(
                    "Could not reach Wikimedia Commons from the current environment."
                ) from exc
            except requests.RequestException as exc:
                raise WikimediaCommonsError("Unable to fetch aircraft photos from Wikimedia Commons.") from exc

        raise WikimediaCommonsError("Unable to fetch aircraft photos from Wikimedia Commons.")

    @classmethod
    def _normalize_page(
        cls,
        page: dict[str, Any],
        registration: str,
    ) -> dict[str, object]:
        title = cls._normalize_text(page.get("title")) or ""
        imageinfo = page.get("imageinfo") or []
        if not isinstance(imageinfo, list) or not imageinfo:
            return {"score": -1, "photo": None}

        info = imageinfo[0]
        if not isinstance(info, dict):
            return {"score": -1, "photo": None}

        thumbnail_url = cls._normalize_text(info.get("thumburl")) or cls._normalize_text(info.get("url"))
        link = cls._normalize_text(info.get("descriptionurl")) or cls._normalize_text(info.get("descriptionshorturl"))
        if not thumbnail_url:
            return {"score": -1, "photo": None}

        extmetadata = info.get("extmetadata") or {}
        if not isinstance(extmetadata, dict):
            extmetadata = {}

        photographer = (
            cls._extract_metadata_value(extmetadata, "Artist")
            or cls._extract_metadata_value(extmetadata, "Credit")
            or cls._normalize_text(info.get("user"))
        )
        license_name = (
            cls._extract_metadata_value(extmetadata, "LicenseShortName")
            or cls._extract_metadata_value(extmetadata, "UsageTerms")
        )
        description = cls._extract_metadata_value(extmetadata, "ImageDescription")

        photo = {
            "thumbnail_url": thumbnail_url,
            "link": link,
            "photographer": photographer,
            "registration": registration,
            "source": "Wikimedia Commons",
            "license": license_name,
            "description": description,
        }
        score = cls._score_candidate(title, registration, description)
        return {"score": score, "photo": photo}

    @classmethod
    def _score_candidate(
        cls,
        title: str,
        registration: str,
        description: str | None,
    ) -> int:
        normalized_title = title.upper()
        normalized_description = (description or "").upper()
        score = 0

        if registration in normalized_title:
            score += 10
        if registration in normalized_description:
            score += 6
        if normalized_title.startswith("FILE:"):
            score += 1
        if any(token in normalized_title for token in ("AIRCRAFT", "BOEING", "AIRBUS", "EMBRAER", "CESSNA")):
            score += 1

        return score

    @classmethod
    def _extract_metadata_value(
        cls,
        metadata: dict[str, Any],
        key: str,
    ) -> str | None:
        value = metadata.get(key)
        if not isinstance(value, dict):
            return None

        return cls._clean_html(value.get("value"))

    @classmethod
    def _clean_html(cls, value: object) -> str | None:
        normalized_value = cls._normalize_text(value)
        if not normalized_value:
            return None

        no_tags = sub(r"<[^>]+>", " ", normalized_value)
        cleaned = " ".join(unescape(no_tags).split())
        return cleaned or None

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned
