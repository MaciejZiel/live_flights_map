from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .provider_base import FlightProviderError


class AircraftPhotoService:
    def __init__(self, providers: Iterable[object]) -> None:
        self.providers = list(providers)

    def fetch_photo(self, registration: str | None) -> dict[str, Any] | None:
        warnings: list[str] = []

        for provider in self.providers:
            try:
                photo = provider.fetch_photo(registration)
            except FlightProviderError as exc:
                warnings.append(str(exc))
                continue

            if photo:
                return photo

        if warnings:
            raise FlightProviderError(" ".join(warnings))

        return None
