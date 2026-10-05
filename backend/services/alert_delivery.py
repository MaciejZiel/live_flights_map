from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urlparse

import requests


class AlertDeliveryError(Exception):
    pass


class InvalidWebhookTargetError(AlertDeliveryError):
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
            raise InvalidWebhookTargetError("Webhook URL must use an allowed HTTP scheme.")
        if parsed.username or parsed.password or not parsed.hostname:
            raise InvalidWebhookTargetError("Webhook URL must not contain credentials and must include a hostname.")
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise InvalidWebhookTargetError("Webhook URL contains an invalid port.") from exc
        self._validate_public_host(parsed.hostname, port)

        try:
            response = self.session.post(
                normalized_url,
                json=event,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
                allow_redirects=False,
            )
            if 300 <= response.status_code < 400:
                raise AlertDeliveryError("Webhook redirects are not followed.")
            response.raise_for_status()
        except InvalidWebhookTargetError:
            raise
        except requests.Timeout as exc:
            raise AlertDeliveryError("Webhook delivery timed out.") from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise AlertDeliveryError(f"Webhook endpoint returned HTTP {status_code}.") from exc
        except requests.RequestException as exc:
            raise AlertDeliveryError("Unable to deliver the alert webhook.") from exc

        return AlertDeliveryResult(status_code=response.status_code)

    @staticmethod
    def _validate_public_host(hostname: str, port: int) -> None:
        normalized_host = hostname.rstrip(".").lower()
        if normalized_host == "localhost" or normalized_host.endswith((".localhost", ".local")):
            raise InvalidWebhookTargetError("Webhook URL must resolve to a public host.")

        try:
            addresses = {ipaddress.ip_address(normalized_host)}
        except ValueError:
            try:
                addresses = {
                    ipaddress.ip_address(result[4][0])
                    for result in socket.getaddrinfo(
                        normalized_host,
                        port,
                        type=socket.SOCK_STREAM,
                    )
                }
            except (OSError, ValueError) as exc:
                raise InvalidWebhookTargetError("Webhook hostname could not be resolved.") from exc

        if not addresses or any(not address.is_global for address in addresses):
            raise InvalidWebhookTargetError("Webhook URL must resolve only to public IP addresses.")
