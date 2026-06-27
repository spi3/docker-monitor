from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from docker_monitor.plugins import DeliveryResult
from docker_monitor.routing import get_alert_field
from docker_monitor.secrets import read_secret_file

DEFAULT_TIMEOUT_SECONDS = 10.0
DISCORD_FIELD_LIMIT = 1024


@dataclass(frozen=True)
class DiscordConfig:
    webhook_url: str
    timeout: float = DEFAULT_TIMEOUT_SECONDS


class DiscordReceiver:
    def __init__(
        self,
        name: str,
        config: DiscordConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.name = name
        self._config = config
        self._client = client or httpx.Client(timeout=config.timeout)

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult:
        try:
            response = self._client.post(
                self._config.webhook_url,
                json=build_discord_payload(alert),
            )
        except TypeError:
            return DeliveryResult.permanent_failure("payload is not JSON serializable")
        except httpx.HTTPError as exc:
            return DeliveryResult.retryable_failure(exc.__class__.__name__)

        if 200 <= response.status_code <= 299:
            return DeliveryResult.success()
        if response.status_code == 429 or response.status_code >= 500:
            return DeliveryResult.retryable_failure(
                f"http status {response.status_code}"
            )
        return DeliveryResult.permanent_failure(f"http status {response.status_code}")


def create_receiver(name: str, config: Mapping[str, Any]) -> DiscordReceiver:
    return DiscordReceiver(name, parse_config(config))


def parse_config(config: Mapping[str, Any]) -> DiscordConfig:
    webhook_url = configured_webhook_url(config)
    timeout = config.get("timeout", DEFAULT_TIMEOUT_SECONDS)
    if not isinstance(timeout, int | float) or isinstance(timeout, bool):
        raise ValueError("discord timeout must be numeric seconds")
    return DiscordConfig(webhook_url=webhook_url, timeout=float(timeout))


def configured_webhook_url(config: Mapping[str, Any]) -> str:
    inline_url = first_string(config, "webhook_url", "WEBHOOK_URL")
    url_file = first_string(config, "webhook_url_file", "WEBHOOK_URL_FILE")

    if inline_url and url_file:
        raise ValueError(
            "discord must configure either webhook_url or webhook_url_file"
        )
    if url_file:
        return read_secret_file(url_file)
    if inline_url:
        return inline_url
    raise ValueError("discord requires webhook_url or webhook_url_file")


def build_discord_payload(alert: Mapping[str, Any]) -> dict[str, Any]:
    status = str(alert.get("status", "firing"))
    container_name = str(get_alert_field(alert, "container.name") or "unknown")
    host = str(alert.get("host", "unknown"))
    health = str(get_alert_field(alert, "container.health") or "unknown")

    return {
        "content": discord_content(status, container_name, host),
        "embeds": [
            {
                "title": discord_title(status),
                "description": f"`{container_name}` on `{host}` is `{health}`.",
                "color": discord_color(status),
                "fields": discord_fields(alert),
            },
        ],
    }


def discord_content(status: str, container_name: str, host: str) -> str:
    if status == "resolved":
        return f"Docker container recovered: {container_name} on {host}"
    if status == "starting":
        return f"Docker container healthcheck starting: {container_name} on {host}"
    return f"Docker container unhealthy: {container_name} on {host}"


def discord_title(status: str) -> str:
    if status == "resolved":
        return "Docker container recovered"
    if status == "starting":
        return "Docker container healthcheck starting"
    return "Docker container unhealthy"


def discord_color(status: str) -> int:
    if status == "resolved":
        return 0x2ECC71
    if status == "starting":
        return 0xF1C40F
    return 0xE74C3C


def discord_fields(alert: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = [
        field("Container", get_alert_field(alert, "container.name")),
        field("Image", get_alert_field(alert, "container.image"), inline=False),
        field("Host", alert.get("host")),
        field("Health", get_alert_field(alert, "container.health")),
        field("Previous", get_alert_field(alert, "container.previous_health")),
        field("Compose Project", get_alert_field(alert, "compose.project")),
        field("Compose Service", get_alert_field(alert, "compose.service")),
    ]

    health_output = get_alert_field(alert, "health_log.output")
    if health_output:
        fields.append(field("Healthcheck Output", health_output, inline=False))

    return [item for item in fields if item is not None]


def field(
    name: str,
    value: object,
    *,
    inline: bool = True,
) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    return {
        "name": name,
        "value": truncate_field(str(value)),
        "inline": inline,
    }


def truncate_field(value: str) -> str:
    return value[:DISCORD_FIELD_LIMIT]


def first_string(config: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = config.get(key)
        if isinstance(value, str) and value:
            return value
    return None
