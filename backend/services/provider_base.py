from __future__ import annotations

from typing import Protocol


class FlightProviderError(Exception):
    pass


class FlightProviderRateLimitError(FlightProviderError):
    pass


class FlightProvider(Protocol):
    name: str

    def fetch_flights(self, bbox: dict[str, float]) -> dict[str, object]: ...
