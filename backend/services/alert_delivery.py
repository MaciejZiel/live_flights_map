from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests


class AlertDeliveryError(Exception):
    pass


@dataclass(slots=True)
class AlertDeliveryResult:
    status_code: int
    delivered_at: str | None = None


class AlertDeliveryService:
    def __init__(
        self,
        *,
        timeout: float,
        allowed_schemes: tuple[str, ...] | list[str],
    ) -> None:
        self.timeout = max(float(timeout or 0), 1.0)
        self.allowed_schemes = {str(scheme).strip().lower() for scheme in allowed_schemes if str(scheme).strip()}
        self.session = requests.Session()

    def deliver_webhook(self, url: str, event: dict[str, object]) -> AlertDeliveryResult:
        normalized_url = str(url or "").strip()
        if not normalized_url:
            raise AlertDeliveryError("Missing webhook URL.")

        parsed = urlparse(normalized_url)
        if parsed.scheme.lower() not in self.allowed_schemes or not parsed.netloc:
            raise AlertDeliveryError("Webhook URL must use an allowed HTTP scheme.")

        try:
            response = self.session.post(
                normalized_url,
                json=event,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise AlertDeliveryError("Webhook delivery timed out.") from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise AlertDeliveryError(f"Webhook endpoint returned HTTP {status_code}.") from exc
        except requests.RequestException as exc:
            raise AlertDeliveryError("Unable to deliver the alert webhook.") from exc

        return AlertDeliveryResult(status_code=response.status_code)
