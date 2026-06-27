from __future__ import annotations

import pytest

from docker_health_alerts.alerts import ContainerSnapshot
from docker_health_alerts.config import MonitorConfig, MonitorFilters
from docker_health_alerts.filters import (
    image_filter_matches,
    is_label_false,
    is_label_true,
    should_monitor_container,
)


def container(
    *,
    name: str = "qbittorrent",
    image: str = "lscr.io/linuxserver/qbittorrent:latest",
    labels: dict[str, str] | None = None,
) -> ContainerSnapshot:
    return ContainerSnapshot(
        id="container-id",
        name=name,
        image=image,
        state="running",
        health="healthy",
        labels=labels or {},
    )


@pytest.mark.parametrize("value", ["true", "TRUE", " true "])
def test_label_opt_in_monitors_true_label(value: str) -> None:
    monitor = MonitorConfig(mode="label_opt_in")

    assert should_monitor_container(
        container(labels={"docker-health-alert.enable": value}),
        monitor,
    )


def test_label_opt_in_ignores_missing_or_false_label() -> None:
    monitor = MonitorConfig(mode="label_opt_in")

    assert not should_monitor_container(container(), monitor)
    assert not should_monitor_container(
        container(labels={"docker-health-alert.enable": "false"}),
        monitor,
    )


def test_label_opt_out_monitors_missing_or_true_label() -> None:
    monitor = MonitorConfig(mode="label_opt_out")

    assert should_monitor_container(container(), monitor)
    assert should_monitor_container(
        container(labels={"docker-health-alert.enable": "true"}),
        monitor,
    )


def test_label_opt_out_excludes_false_label() -> None:
    monitor = MonitorConfig(mode="label_opt_out")

    assert not should_monitor_container(
        container(labels={"docker-health-alert.enable": " false "}),
        monitor,
    )


def test_optional_name_filter_matches_normalized_name() -> None:
    monitor = MonitorConfig(
        mode="label_opt_out",
        filters=MonitorFilters(names=["qbittorrent"]),
    )

    assert should_monitor_container(container(name="/qbittorrent"), monitor)
    assert not should_monitor_container(container(name="/sonarr"), monitor)


def test_optional_image_filter_matches_repository_or_reference() -> None:
    monitor = MonitorConfig(
        mode="label_opt_out",
        filters=MonitorFilters(images=["lscr.io/linuxserver/qbittorrent"]),
    )

    assert should_monitor_container(
        container(image="lscr.io/linuxserver/qbittorrent:latest"),
        monitor,
    )
    assert not should_monitor_container(
        container(image="linuxserver/sonarr:latest"),
        monitor,
    )


def test_optional_compose_filters_match_labels() -> None:
    monitor = MonitorConfig(
        mode="label_opt_out",
        filters=MonitorFilters(
            compose_projects=["gt"],
            compose_services=["qbittorrent"],
        ),
    )

    assert should_monitor_container(
        container(
            labels={
                "com.docker.compose.project": "gt",
                "com.docker.compose.service": "qbittorrent",
            },
        ),
        monitor,
    )
    assert not should_monitor_container(
        container(
            labels={
                "com.docker.compose.project": "gt",
                "com.docker.compose.service": "sonarr",
            },
        ),
        monitor,
    )


def test_optional_arbitrary_label_filters_require_all_matches() -> None:
    monitor = MonitorConfig(
        mode="label_opt_out",
        filters=MonitorFilters(
            labels={
                "com.example.tier": "media",
                "com.example.alerts": "enabled",
            },
        ),
    )

    assert should_monitor_container(
        container(
            labels={
                "com.example.tier": "media",
                "com.example.alerts": "enabled",
            },
        ),
        monitor,
    )
    assert not should_monitor_container(
        container(labels={"com.example.tier": "media"}),
        monitor,
    )


def test_label_bool_helpers_are_case_insensitive() -> None:
    assert is_label_true(" TRUE ")
    assert is_label_false(" FALSE ")
    assert not is_label_true("yes")
    assert not is_label_false(None)


def test_image_filter_matches_digest_and_tag() -> None:
    assert image_filter_matches("repo/app:latest", "repo/app")
    assert image_filter_matches("repo/app@sha256:abc", "repo/app")
    assert image_filter_matches("repo/app:latest", "repo/app:latest")
    assert not image_filter_matches("repo/application:latest", "repo/app")
