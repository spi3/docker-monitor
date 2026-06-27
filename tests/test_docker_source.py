from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from docker_health_alerts.docker_source import (
    DOCKER_EVENT_FILTERS,
    DockerSource,
    container_has_healthcheck,
    parse_health_status_event,
    snapshot_from_container_attrs,
)


def container_attrs(
    *,
    health_status: str = "unhealthy",
    healthcheck: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "Id": "abc123",
        "Name": "/qbittorrent",
        "Config": {
            "Image": "lscr.io/linuxserver/qbittorrent:latest",
            "Labels": {
                "docker-health-alert.enable": "true",
                "com.docker.compose.project": "gt",
            },
            "Healthcheck": healthcheck or {"Test": ["CMD", "curl", "-f", "/"]},
        },
        "State": {
            "Status": "running",
            "Health": {
                "Status": health_status,
                "Log": [
                    {"ExitCode": 0, "Output": "ok"},
                    {"ExitCode": 1, "Output": "failed"},
                ],
            },
        },
    }


def test_snapshot_from_container_attrs_extracts_health_metadata() -> None:
    snapshot = snapshot_from_container_attrs(container_attrs())

    assert snapshot.id == "abc123"
    assert snapshot.name == "/qbittorrent"
    assert snapshot.image == "lscr.io/linuxserver/qbittorrent:latest"
    assert snapshot.state == "running"
    assert snapshot.health == "unhealthy"
    assert snapshot.labels["com.docker.compose.project"] == "gt"
    assert snapshot.health_log is not None
    assert snapshot.health_log.exit_code == 1
    assert snapshot.health_log.output == "failed"
    assert snapshot.has_healthcheck is True


def test_container_without_health_state_or_healthcheck_is_not_healthchecked() -> None:
    attrs = {
        "Id": "abc123",
        "Name": "/no-health",
        "Config": {"Image": "busybox", "Healthcheck": {"Test": ["NONE"]}},
        "State": {"Status": "running"},
    }

    assert not container_has_healthcheck(attrs)
    assert snapshot_from_container_attrs(attrs).has_healthcheck is False


def test_parse_health_status_event_from_actor_attributes() -> None:
    event = parse_health_status_event(
        {
            "id": "abc123",
            "Actor": {"Attributes": {"health_status": "healthy"}},
            "timeNano": 1_782_518_400_000_000_000,
        },
    )

    assert event is not None
    assert event.container_id == "abc123"
    assert event.health == "healthy"
    assert event.time == datetime(2026, 6, 27, 0, 0, tzinfo=UTC)


def test_parse_health_status_event_from_status_fallback() -> None:
    event = parse_health_status_event(
        {
            "Actor": {"ID": "abc123", "Attributes": {}},
            "status": "health_status: unhealthy",
            "time": 1_782_518_400,
        },
    )

    assert event is not None
    assert event.container_id == "abc123"
    assert event.health == "unhealthy"


def test_docker_event_filters_are_health_status_only() -> None:
    assert DOCKER_EVENT_FILTERS == {"type": "container", "event": "health_status"}


def test_docker_source_uses_from_env_client(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeContainers:
        def list(self, *, all: bool) -> list[Any]:
            assert all is True
            return []

    class FakeClient:
        containers = FakeContainers()

    fake_client = FakeClient()
    monkeypatch.setattr(
        "docker_health_alerts.docker_source.docker.from_env", lambda: fake_client
    )

    source = DockerSource()

    assert source.list_containers() == []
