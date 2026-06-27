from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from docker_monitor.plugins import DeliveryResult
from docker_monitor.receivers.generic_webhook import (
    GenericWebhookReceiver,
    configured_headers,
    create_receiver,
    parse_config,
    render_payload,
)


def alert() -> dict[str, Any]:
    return {
        "status": "firing",
        "severity": "warning",
        "container": {
            "name": "qbittorrent",
            "health": "unhealthy",
        },
    }


def test_url_file_loading_strips_one_trailing_newline(tmp_path: Path) -> None:
    url_file = tmp_path / "webhook_url"
    url_file.write_text("https://example.invalid/webhook\n", encoding="utf-8")

    config = parse_config({"url_file": str(url_file)})

    assert config.url == "https://example.invalid/webhook"


def test_static_and_file_loaded_headers_are_applied(tmp_path: Path) -> None:
    header_file = tmp_path / "authorization"
    header_file.write_text("Bearer secret\n", encoding="utf-8")

    headers = configured_headers(
        {
            "headers": {"X-Source": "docker-monitor"},
            "header_files": {"Authorization": str(header_file)},
        },
    )

    assert headers == {
        "X-Source": "docker-monitor",
        "Authorization": "Bearer secret",
    }


def test_default_payload_sends_normalized_alert_object() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    receiver = GenericWebhookReceiver(
        "raw-webhook",
        parse_config({"url": "https://example.invalid/webhook"}),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = receiver.deliver(alert())

    assert result == DeliveryResult.success()
    assert json.loads(requests[0].content) == alert()


def test_create_receiver_applies_headers_to_request(tmp_path: Path) -> None:
    header_file = tmp_path / "authorization"
    header_file.write_text("Bearer secret\n", encoding="utf-8")
    captured_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.append(request.headers)
        return httpx.Response(200)

    receiver = create_receiver(
        "raw-webhook",
        {
            "url": "https://example.invalid/webhook",
            "headers": {"X-Source": "docker-monitor"},
            "header_files": {"Authorization": str(header_file)},
        },
    )
    receiver._client = httpx.Client(transport=httpx.MockTransport(handler))  # noqa: SLF001

    result = receiver.deliver(alert())

    assert result.status == "success"
    assert captured_headers[0]["X-Source"] == "docker-monitor"
    assert captured_headers[0]["Authorization"] == "Bearer secret"


def test_non_2xx_response_is_retryable_without_url_leak() -> None:
    receiver = GenericWebhookReceiver(
        "raw-webhook",
        parse_config({"url": "https://secret.example/webhook"}),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(500))
        ),
    )

    result = receiver.deliver(alert())

    assert result.status == "retryable_failure"
    assert result.message == "http status 500"
    assert "secret.example" not in result.message


def test_network_error_is_retryable_without_url_leak() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("https://secret.example/webhook", request=request)

    receiver = GenericWebhookReceiver(
        "raw-webhook",
        parse_config({"url": "https://secret.example/webhook"}),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = receiver.deliver(alert())

    assert result.status == "retryable_failure"
    assert result.message == "ConnectError"
    assert "secret.example" not in result.message


def test_payload_template_renders_json_payload() -> None:
    payload = render_payload(
        {
            "text": "{container.name} is {status}",
            "labels": ["{severity}", "{container.health}"],
            "unchanged": 5,
        },
        alert(),
    )

    assert payload == {
        "text": "qbittorrent is firing",
        "labels": ["warning", "unhealthy"],
        "unchanged": 5,
    }


def test_payload_template_is_sent(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    receiver = GenericWebhookReceiver(
        "raw-webhook",
        parse_config(
            {
                "url": "https://example.invalid/webhook",
                "payload_template": {"message": "{container.name} {status}"},
            },
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = receiver.deliver(alert())

    assert result.status == "success"
    assert json.loads(requests[0].content) == {"message": "qbittorrent firing"}


def test_secret_values_do_not_appear_in_failure_messages(tmp_path: Path) -> None:
    url_file = tmp_path / "url"
    url_file.write_text("https://secret.example/webhook\n", encoding="utf-8")
    header_file = tmp_path / "authorization"
    header_file.write_text("Bearer secret-value\n", encoding="utf-8")
    receiver = GenericWebhookReceiver(
        "raw-webhook",
        parse_config(
            {
                "url_file": str(url_file),
                "header_files": {"Authorization": str(header_file)},
            },
        ),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        ),
    )

    result = receiver.deliver(alert())

    assert result.status == "retryable_failure"
    assert "secret.example" not in result.message
    assert "secret-value" not in result.message
