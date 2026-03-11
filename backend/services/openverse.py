from __future__ import annotations

from typing import Any

import requests

from .provider_base import FlightProviderError, FlightProviderRateLimitError


class OpenverseError(FlightProviderError):
    pass


class OpenverseRateLimitError(FlightProviderRateLimitError, OpenverseError):
    pass


class OpenverseClient:
    name = "openverse"

    def __init__(self, base_url: str, timeout: float, max_retries: int) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max(max_retries, 0)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "live-flights-map/0.1 (Openverse aircraft photo lookup)",
            }
        )

    def fetch_photo(self, registration: str | None) -> dict[str, Any] | None:
        normalized_registration = self._normalize_text(registration, uppercase=True)
        if not normalized_registration:
            return None

        return self.fetch_photo_query(
            normalized_registration,
            registration=normalized_registration,
        )

    def fetch_photo_query(
        self,
        query: str,
        *,
        registration: str | None = None,
        type_code: str | None = None,
        operator_code: str | None = None,
        airline_code: str | None = None,
        airline_name: str | None = None,
    ) -> dict[str, Any] | None:
        normalized_query = self._normalize_text(query)
        if not normalized_query:
            return None

        normalized_registration = self._normalize_text(registration, uppercase=True)
        normalized_type_code = self._normalize_text(type_code, uppercase=True)
        normalized_operator_code = self._normalize_text(operator_code, uppercase=True)
        normalized_airline_code = self._normalize_text(airline_code, uppercase=True)
        normalized_airline_name = self._normalize_text(airline_name)

        response = self._request_photo_lookup(normalized_query)
        payload = response.json()
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            return None

        normalized_results = sorted(
            (
                self._normalize_result(
                    result,
                    registration=normalized_registration,
                    type_code=normalized_type_code,
                    operator_code=normalized_operator_code,
                    airline_code=normalized_airline_code,
                    airline_name=normalized_airline_name,
                )
                for result in results
                if isinstance(result, dict)
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        normalized_results = [item for item in normalized_results if item["photo"] and item["score"] > 0]
        if not normalized_results:
            return None

        return normalized_results[0]["photo"]

    def _request_photo_lookup(self, query: str) -> requests.Response:
        params = {
            "q": query,
            "page_size": 6,
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
                raise OpenverseError("Openverse photo lookup timed out.") from exc
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code == 429:
                    raise OpenverseRateLimitError("Openverse photo lookup rate limited.") from exc
                raise OpenverseError(
                    f"Openverse photo lookup returned HTTP {status_code}."
                ) from exc
            except requests.ConnectionError as exc:
                if attempt < self.max_retries:
                    continue
                raise OpenverseError("Could not reach Openverse from the current environment.") from exc
            except requests.RequestException as exc:
                raise OpenverseError("Unable to fetch aircraft photos from Openverse.") from exc

        raise OpenverseError("Unable to fetch aircraft photos from Openverse.")

    @classmethod
    def _normalize_result(
        cls,
        result: dict[str, Any],
        *,
        registration: str | None,
        type_code: str | None,
        operator_code: str | None,
        airline_code: str | None,
        airline_name: str | None,
    ) -> dict[str, object]:
        if result.get("mature"):
            return {"score": -1, "photo": None}

        url = cls._normalize_text(result.get("url"))
        thumbnail_url = cls._normalize_text(result.get("thumbnail")) or url
        link = cls._normalize_text(result.get("foreign_landing_url")) or cls._normalize_text(
            result.get("detail_url")
        )
        if not thumbnail_url:
            return {"score": -1, "photo": None}

        title = cls._normalize_text(result.get("title")) or ""
        creator = cls._normalize_text(result.get("creator"))
        license_name = cls._normalize_license(
            result.get("license"),
            result.get("license_version"),
        )
        source = cls._normalize_text(result.get("provider")) or cls._normalize_text(result.get("source"))
        attribution = cls._normalize_text(result.get("attribution"))
        tags = result.get("tags") or []
        if not isinstance(tags, list):
            tags = []

        photo = {
            "thumbnail_url": thumbnail_url,
            "link": link,
            "photographer": creator,
            "registration": registration,
            "source": f"Openverse · {source}" if source else "Openverse",
            "license": license_name,
            "attribution": attribution,
        }
        score = cls._score_candidate(
            title=title,
            registration=registration,
            tags=tags,
            fields_matched=result.get("fields_matched") or [],
            type_code=type_code,
            operator_code=operator_code,
            airline_code=airline_code,
            airline_name=airline_name,
        )
        return {"score": score, "photo": photo}

    @classmethod
    def _score_candidate(
        cls,
        *,
        title: str,
        registration: str | None,
        tags: list[object],
        fields_matched: list[object],
        type_code: str | None,
        operator_code: str | None,
        airline_code: str | None,
        airline_name: str | None,
    ) -> int:
        normalized_title = title.upper()
        normalized_registration = registration.upper() if registration else None
        normalized_tags = {
            cls._normalize_text(tag.get("name"), uppercase=True)
            for tag in tags
            if isinstance(tag, dict)
        }
        normalized_tags.discard(None)
        normalized_fields = {
            cls._normalize_text(field)
            for field in fields_matched
            if cls._normalize_text(field)
        }

        score = 0
        if normalized_registration and normalized_title == normalized_registration:
            score += 14
        elif normalized_registration and normalized_registration in normalized_title:
            score += 10

        if normalized_registration and normalized_registration in normalized_tags:
            score += 8

        if "tags.name" in normalized_fields:
            score += 2

        if "title" in normalized_fields:
            score += 1

        for token in (type_code, operator_code, airline_code, airline_name):
            normalized_token = cls._normalize_text(token, uppercase=True)
            if not normalized_token:
                continue
            if normalized_token in normalized_title:
                score += 3
            if normalized_token in normalized_tags:
                score += 4

        return score

    @staticmethod
    def _normalize_license(license_code: object, license_version: object) -> str | None:
        normalized_code = OpenverseClient._normalize_text(license_code, uppercase=True)
        normalized_version = OpenverseClient._normalize_text(license_version)
        if not normalized_code:
            return None
        return f"{normalized_code} {normalized_version}".strip() if normalized_version else normalized_code

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned
