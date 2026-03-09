from __future__ import annotations

from typing import Any

import requests

from .provider_base import FlightProviderError, FlightProviderRateLimitError


class PlanespottingError(FlightProviderError):
    pass


class PlanespottingRateLimitError(FlightProviderRateLimitError, PlanespottingError):
    pass


class PlanespottingClient:
    name = "planespotting"

    def __init__(self, base_url: str, timeout: float, max_retries: int) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max(max_retries, 0)
        self.session = requests.Session()

    def fetch_photo(self, registration: str | None) -> dict[str, Any] | None:
        normalized_registration = self._normalize_text(registration, uppercase=True)
        if not normalized_registration:
            return None

        response = self._request_photo_lookup(normalized_registration)
        payload = response.json()
        photos = payload.get("photos") or payload.get("images") or []
        if not isinstance(photos, list) or not photos:
            return None

        photo = photos[0]
        if not isinstance(photo, dict):
            return None

        thumbnail = photo.get("thumbnail")
        thumbnail_url = None
        if isinstance(thumbnail, dict):
            thumbnail_url = self._normalize_text(thumbnail.get("src"))
        else:
            thumbnail_url = self._normalize_text(thumbnail)

        if not thumbnail_url:
            return None

        return {
            "thumbnail_url": thumbnail_url,
            "link": self._normalize_text(photo.get("link")),
            "photographer": self._normalize_text(photo.get("photographer"))
            or self._normalize_text(photo.get("user")),
            "registration": self._normalize_text(photo.get("registration"), uppercase=True)
            or normalized_registration,
            "source": "planespotting.be",
        }

    def _request_photo_lookup(self, registration: str) -> requests.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    self.base_url,
                    params={"registration": registration},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response
            except requests.Timeout as exc:
                if attempt < self.max_retries:
                    continue
                raise PlanespottingError("Aircraft photo lookup timed out.") from exc
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code == 429:
                    raise PlanespottingRateLimitError("Aircraft photo lookup rate limited.") from exc
                raise PlanespottingError(
                    f"Aircraft photo lookup returned HTTP {status_code}."
                ) from exc
            except requests.ConnectionError as exc:
                if attempt < self.max_retries:
                    continue
                raise PlanespottingError(
                    "Could not reach Planespotting from the current environment."
                ) from exc
            except requests.RequestException as exc:
                raise PlanespottingError("Unable to fetch aircraft photos.") from exc

        raise PlanespottingError("Unable to fetch aircraft photos.")

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned
