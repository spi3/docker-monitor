from __future__ import annotations

from typing import Any

from docker_health_alerts.config import RouteConfig
from docker_health_alerts.routing import get_alert_field, route_alert, route_matches


def alert_payload() -> dict[str, Any]:
    return {
        "version": "1",
        "status": "firing",
        "alert": "DockerContainerUnhealthy",
        "host": "serenity",
        "severity": "warning",
        "container": {
            "name": "qbittorrent",
            "image": "lscr.io/linuxserver/qbittorrent:latest",
            "health": "unhealthy",
        },
        "compose": {
            "project": "gt",
            "service": "qbittorrent",
        },
    }


def test_route_matches_exact_top_level_field() -> None:
    route = RouteConfig(match={"severity": "warning"}, receivers=["discord-lab"])

    assert route_matches(route, alert_payload())


def test_route_matches_exact_nested_field() -> None:
    route = RouteConfig(
        match={
            "container.name": "qbittorrent",
            "compose.project": "gt",
        },
        receivers=["discord-lab"],
    )

    assert route_matches(route, alert_payload())


def test_route_rejects_missing_or_different_field() -> None:
    assert not route_matches(
        RouteConfig(match={"compose.service": "sonarr"}, receivers=["discord-lab"]),
        alert_payload(),
    )
    assert get_alert_field(alert_payload(), "container.missing") is None


def test_route_alert_returns_deduplicated_receivers_in_order() -> None:
    routes = [
        RouteConfig(match={"severity": "warning"}, receivers=["discord-lab"]),
        RouteConfig(
            match={"status": "firing"},
            receivers=["discord-lab", "raw-webhook"],
        ),
    ]

    assert route_alert(alert_payload(), routes) == ["discord-lab", "raw-webhook"]


def test_route_alert_logs_unmatched_alert() -> None:
    logs: list[dict[str, Any]] = []

    receivers = route_alert(
        alert_payload(),
        [RouteConfig(match={"severity": "critical"}, receivers=["discord-lab"])],
        log_event=logs.append,
    )

    assert receivers == []
    assert logs == [
        {
            "event": "route.unmatched",
            "alert_status": "firing",
            "alert": "DockerContainerUnhealthy",
        },
    ]
