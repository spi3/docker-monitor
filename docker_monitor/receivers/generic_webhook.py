from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from docker_monitor.plugins import DeliveryResult
from docker_monitor.routing import get_alert_field
from docker_monitor.secrets import read_secret_file

DEFAULT_TIMEOUT_SECONDS = 10.0
_TEMPLATE_FIELD_RE = re.compile(r"{([A-Za-z0-9_.-]+)}")


@dataclass(frozen=True)
class GenericWebhookConfig:
    url: str
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    headers: dict[str, str] | None = None
    payload_template: Any | None = None


class GenericWebhookReceiver:
    def __init__(
        self,
        name: str,
        config: GenericWebhookConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.name = name
        self._config = config
        self._client = client or httpx.Client(timeout=config.timeout)

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult:
        payload = render_payload(self._config.payload_template, alert)
        try:
            response = self._client.post(
                self._config.url,
                headers=self._config.headers,
                json=payload,
            )
        except TypeError:
            return DeliveryResult.permanent_failure("payload is not JSON serializable")
        except httpx.HTTPError as exc:
            return DeliveryResult.retryable_failure(exc.__class__.__name__)

        if 200 <= response.status_code <= 299:
            return DeliveryResult.success()

        return DeliveryResult.retryable_failure(f"http status {response.status_code}")


def create_receiver(
    name: str,
    config: Mapping[str, Any],
) -> GenericWebhookReceiver:
    return GenericWebhookReceiver(name, parse_config(config))


def parse_config(config: Mapping[str, Any]) -> GenericWebhookConfig:
    url = configured_url(config)
    headers = configured_headers(config)
    timeout = config.get("timeout", DEFAULT_TIMEOUT_SECONDS)
    if not isinstance(timeout, int | float) or isinstance(timeout, bool):
        raise ValueError("generic-webhook timeout must be numeric seconds")

    return GenericWebhookConfig(
        url=url,
        timeout=float(timeout),
        headers=headers,
        payload_template=config.get("payload_template"),
    )


def configured_url(config: Mapping[str, Any]) -> str:
    inline_url = first_string(config, "url", "WEBHOOK_URL")
    url_file = first_string(config, "url_file", "WEBHOOK_URL_FILE")

    if inline_url and url_file:
        raise ValueError("generic-webhook must configure either url or url_file")
    if url_file:
        return read_secret_file(url_file)
    if inline_url:
        return inline_url
    raise ValueError("generic-webhook requires url or url_file")


def configured_headers(config: Mapping[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}

    raw_headers = config.get("headers", {})
    if raw_headers:
        if not isinstance(raw_headers, Mapping):
            raise ValueError("generic-webhook headers must be a mapping")
        headers.update(string_mapping(raw_headers, "headers"))

    raw_header_files = config.get("header_files", {})
    if raw_header_files:
        if not isinstance(raw_header_files, Mapping):
            raise ValueError("generic-webhook header_files must be a mapping")
        for header_name, path in string_mapping(
            raw_header_files, "header_files"
        ).items():
            headers[header_name] = read_secret_file(path)

    return headers


def render_payload(template: Any | None, alert: Mapping[str, Any]) -> Any:
    if template is None:
        return dict(alert)
    if isinstance(template, str):
        return render_template_string(template, alert)
    if isinstance(template, list):
        return [render_payload(item, alert) for item in template]
    if isinstance(template, Mapping):
        return {
            str(key): render_payload(value, alert) for key, value in template.items()
        }
    return template


def render_template_string(template: str, alert: Mapping[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = get_alert_field(alert, match.group(1))
        return "" if value is None else str(value)

    return _TEMPLATE_FIELD_RE.sub(replace, template)


def first_string(config: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = config.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def string_mapping(value: Mapping[Any, Any], field_name: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or not isinstance(item_value, str):
            raise ValueError(f"generic-webhook {field_name} must contain strings")
        result[item_key] = item_value
    return result
