from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from .provider_base import FlightProviderError


class AircraftPhotoProxyError(FlightProviderError):
    pass


@dataclass(slots=True)
class AircraftPhotoAsset:
    body: bytes
    content_type: str
    etag: str | None = None


class AircraftPhotoProxyService:
    def __init__(
        self,
        *,
        timeout: float,
        allowed_hosts: tuple[str, ...],
        cache_service=None,
        cache_ttl_seconds: float = 86400,
    ) -> None:
        self.timeout = timeout
        self.allowed_hosts = tuple(
            host.strip().lower() for host in allowed_hosts if str(host).strip()
        )
        self.cache_service = cache_service
        self.cache_ttl_seconds = max(float(cache_ttl_seconds or 0), 300.0)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "live-flights-map/0.1 (aircraft photo proxy)",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            }
        )

    def fetch_asset(self, url: str) -> AircraftPhotoAsset:
        normalized_url = self._normalize_url(url)
        self._validate_url(normalized_url)
        if self.cache_service is not None:
            cached = self.cache_service.get_asset(normalized_url)
            if isinstance(cached, dict) and isinstance(cached.get("body"), (bytes, bytearray)):
                return AircraftPhotoAsset(
                    body=bytes(cached["body"]),
                    content_type=self._normalize_content_type(cached.get("content_type")),
                    etag=self._normalize_text(cached.get("etag")),
                )

        try:
            response = self.session.get(
                normalized_url,
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise AircraftPhotoProxyError("Aircraft photo download timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise AircraftPhotoProxyError("Unable to download the aircraft photo.") from exc

        content_type = self._normalize_content_type(response.headers.get("Content-Type"))
        if not content_type.startswith("image/"):
            raise AircraftPhotoProxyError("The aircraft photo source did not return an image.")

        asset = AircraftPhotoAsset(
            body=response.content,
            content_type=content_type,
            etag=self._normalize_text(response.headers.get("ETag")),
        )
        if self.cache_service is not None:
            self.cache_service.store_asset(
                normalized_url,
                body=asset.body,
                content_type=asset.content_type,
                etag=asset.etag,
                ttl_seconds=self.cache_ttl_seconds,
            )
        return asset

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise AircraftPhotoProxyError("Unsupported aircraft photo URL.")

        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            raise AircraftPhotoProxyError("Missing aircraft photo host.")

        if not self._is_allowed_host(hostname):
            raise AircraftPhotoProxyError("Blocked aircraft photo host.")

    def _is_allowed_host(self, hostname: str) -> bool:
        return any(
            hostname == allowed_host or hostname.endswith(f".{allowed_host}")
            for allowed_host in self.allowed_hosts
        )

    @staticmethod
    def _normalize_url(url: str | None) -> str:
        if url is None:
            raise AircraftPhotoProxyError("Missing aircraft photo URL.")
        cleaned = str(url).strip()
        if not cleaned:
            raise AircraftPhotoProxyError("Missing aircraft photo URL.")
        return cleaned

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned

    @staticmethod
    def _normalize_content_type(value: str | None) -> str:
        if value is None:
            return "application/octet-stream"
        return value.split(";", 1)[0].strip().lower() or "application/octet-stream"
