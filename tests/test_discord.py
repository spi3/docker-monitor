from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from docker_monitor.receivers.discord import (
    DiscordReceiver,
    build_discord_payload,
    parse_config,
)


def alert(status: str = "firing") -> dict[str, Any]:
    return {
        "status": status,
        "host": "serenity",
        "container": {
            "name": "qbittorrent",
            "image": "lscr.io/linuxserver/qbittorrent:latest",
            "health": "unhealthy" if status == "firing" else "healthy",
            "previous_health": "healthy" if status == "firing" else "unhealthy",
        },
        "compose": {
            "project": "gt",
            "service": "qbittorrent",
        },
        "health_log": {
            "output": "healthcheck failed",
        },
    }


def test_webhook_url_file_loading_strips_one_trailing_newline(tmp_path: Path) -> None:
    webhook_file = tmp_path / "discord_webhook"
    webhook_file.write_text("https://discord.example/webhook\n", encoding="utf-8")

    config = parse_config({"webhook_url_file": str(webhook_file)})

    assert config.webhook_url == "https://discord.example/webhook"


def test_firing_payload_identifies_unhealthy_container() -> None:
    payload = build_discord_payload(alert("firing"))

    assert payload["content"] == "Docker container unhealthy: qbittorrent on serenity"
    assert payload["embeds"][0]["title"] == "Docker container unhealthy"
    assert payload["embeds"][0]["color"] == 0xE74C3C
    assert {"name": "Health", "value": "unhealthy", "inline": True} in payload[
        "embeds"
    ][0]["fields"]


def test_resolved_payload_identifies_recovered_container() -> None:
    payload = build_discord_payload(alert("resolved"))

    assert payload["content"] == "Docker container recovered: qbittorrent on serenity"
    assert payload["embeds"][0]["title"] == "Docker container recovered"
    assert payload["embeds"][0]["color"] == 0x2ECC71


def test_starting_payload_is_supported() -> None:
    payload = build_discord_payload(alert("starting"))

    assert (
        payload["content"]
        == "Docker container healthcheck starting: qbittorrent on serenity"
    )
    assert payload["embeds"][0]["title"] == "Docker container healthcheck starting"
    assert payload["embeds"][0]["color"] == 0xF1C40F


def test_discord_delivery_posts_payload_and_returns_success() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    receiver = DiscordReceiver(
        "discord-lab",
        parse_config({"webhook_url": "https://discord.example/webhook"}),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = receiver.deliver(alert("firing"))

    assert result.status == "success"
    payload = json.loads(requests[0].content)
    assert payload["content"] == "Docker container unhealthy: qbittorrent on serenity"


def test_network_error_is_retryable_without_url_leak() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("https://secret.discord/webhook", request=request)

    receiver = DiscordReceiver(
        "discord-lab",
        parse_config({"webhook_url": "https://secret.discord/webhook"}),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = receiver.deliver(alert("firing"))

    assert result.status == "retryable_failure"
    assert result.message == "ConnectError"
    assert "secret.discord" not in result.message


def test_5xx_and_429_are_retryable_and_4xx_is_permanent() -> None:
    retry_receiver = DiscordReceiver(
        "discord-lab",
        parse_config({"webhook_url": "https://discord.example/webhook"}),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(500)),
        ),
    )
    rate_limit_receiver = DiscordReceiver(
        "discord-lab",
        parse_config({"webhook_url": "https://discord.example/webhook"}),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(429)),
        ),
    )
    permanent_receiver = DiscordReceiver(
        "discord-lab",
        parse_config({"webhook_url": "https://discord.example/webhook"}),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404)),
        ),
    )

    assert retry_receiver.deliver(alert("firing")).status == "retryable_failure"
    assert rate_limit_receiver.deliver(alert("firing")).status == "retryable_failure"
    assert permanent_receiver.deliver(alert("firing")).status == "permanent_failure"


def test_discord_webhook_url_is_not_in_failure_message() -> None:
    receiver = DiscordReceiver(
        "discord-lab",
        parse_config({"webhook_url": "https://secret.discord/webhook"}),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503)),
        ),
    )

    result = receiver.deliver(alert("firing"))

    assert result.status == "retryable_failure"
    assert "secret.discord" not in result.message
