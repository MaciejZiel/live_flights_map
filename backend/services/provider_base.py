from __future__ import annotations

from typing import Protocol


class FlightProviderError(Exception):
    pass


class FlightProviderRateLimitError(FlightProviderError):
    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def parse_retry_after_seconds(headers: object) -> float | None:
    if not hasattr(headers, "get"):
        return None
    for header_name in ("X-Rate-Limit-Retry-After-Seconds", "Retry-After"):
        value = headers.get(header_name)
        if value is None:
            continue
        try:
            retry_after = float(value)
        except (TypeError, ValueError):
            continue
        if retry_after > 0:
            return retry_after
    return None


class FlightProvider(Protocol):
    name: str

    def fetch_flights(self, bbox: dict[str, float]) -> dict[str, object]: ...
