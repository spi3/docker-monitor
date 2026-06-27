from __future__ import annotations

from datetime import UTC, datetime

import pytest

from docker_health_alerts.alerts import (
    REDACTED_VALUE,
    AlertStatus,
    ContainerSnapshot,
    HealthLogSnapshot,
    alert_status_for_health,
    build_alert,
    format_event_time,
    normalize_container_name,
    redact_labels,
    truncate_health_output,
)


def test_build_alert_populates_normalized_schema() -> None:
    container = ContainerSnapshot(
        id="abc123",
        name="/qbittorrent",
        image="lscr.io/linuxserver/qbittorrent:latest",
        state="running",
        health="unhealthy",
        labels={
            "docker-health-alert.enable": "true",
            "com.docker.compose.project": "gt",
            "com.docker.compose.service": "qbittorrent",
            "com.example.api_token": "secret-token",
        },
        health_log=HealthLogSnapshot(exit_code=1, output="healthcheck failed"),
    )

    alert = build_alert(
        status="firing",
        host="serenity",
        container=container,
        previous_health="healthy",
        event_time=datetime(2026, 6, 27, 17, 0, tzinfo=UTC),
        health_log_output_limit=11,
    )
    payload = alert.to_dict()

    assert payload == {
        "version": "1",
        "status": "firing",
        "alert": "DockerContainerUnhealthy",
        "host": "serenity",
        "severity": "warning",
        "container": {
            "id": "abc123",
            "name": "qbittorrent",
            "image": "lscr.io/linuxserver/qbittorrent:latest",
            "state": "running",
            "health": "unhealthy",
            "previous_health": "healthy",
        },
        "compose": {
            "project": "gt",
            "service": "qbittorrent",
        },
        "labels": {
            "docker-health-alert.enable": "true",
            "com.docker.compose.project": "gt",
            "com.docker.compose.service": "qbittorrent",
            "com.example.api_token": REDACTED_VALUE,
        },
        "event": {
            "source": "docker",
            "time": "2026-06-27T17:00:00Z",
        },
        "health_log": {
            "exit_code": 1,
            "output": "healthcheck",
        },
    }


@pytest.mark.parametrize(
    "health, send_resolved, send_starting, expected",
    [
        ("unhealthy", True, False, "firing"),
        ("healthy", True, False, "resolved"),
        ("healthy", False, False, None),
        ("starting", True, True, "starting"),
        ("starting", True, False, None),
        ("none", True, True, None),
    ],
)
def test_alert_status_for_health(
    health: str,
    send_resolved: bool,
    send_starting: bool,
    expected: AlertStatus | None,
) -> None:
    assert (
        alert_status_for_health(
            health,
            send_resolved=send_resolved,
            send_starting=send_starting,
        )
        == expected
    )


def test_redact_labels_is_case_insensitive() -> None:
    labels = {
        "ApiToken": "abc",
        "SECRET_KEY": "def",
        "authorization": "ghi",
        "com.example.owner": "media",
    }

    assert redact_labels(labels) == {
        "ApiToken": REDACTED_VALUE,
        "SECRET_KEY": REDACTED_VALUE,
        "authorization": REDACTED_VALUE,
        "com.example.owner": "media",
    }


def test_truncate_health_output_respects_limit() -> None:
    assert truncate_health_output("abcdef", 3) == "abc"
    assert truncate_health_output("abcdef", 0) == ""
    assert truncate_health_output(None, 3) is None


def test_format_event_time_assumes_utc_for_naive_datetime() -> None:
    assert format_event_time(datetime(2026, 6, 27, 17, 0)) == "2026-06-27T17:00:00Z"


def test_normalize_container_name_removes_leading_slash() -> None:
    assert normalize_container_name("/qbittorrent") == "qbittorrent"
    assert normalize_container_name("sonarr") == "sonarr"
