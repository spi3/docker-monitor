from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from docker_health_alerts.alerts import ContainerSnapshot, HealthLogSnapshot
from docker_health_alerts.config import AppConfig, MonitorConfig
from docker_health_alerts.reconciliation import reconcile_startup, startup_alert_status
from docker_health_alerts.state import HealthStateTracker


@dataclass
class FakeSource:
    containers: list[ContainerSnapshot]

    def list_containers(self) -> list[ContainerSnapshot]:
        return self.containers


def container(
    *,
    id: str = "container-id",
    name: str = "qbittorrent",
    health: str = "healthy",
    labels: dict[str, str] | None = None,
    has_healthcheck: bool = True,
    health_log: HealthLogSnapshot | None = None,
) -> ContainerSnapshot:
    return ContainerSnapshot(
        id=id,
        name=name,
        image="lscr.io/linuxserver/qbittorrent:latest",
        state="running",
        health=health,
        labels=labels if labels is not None else {"docker-health-alert.enable": "true"},
        health_log=health_log,
        has_healthcheck=has_healthcheck,
    )


def test_reconcile_startup_emits_firing_for_existing_unhealthy_container() -> None:
    tracker = HealthStateTracker()
    config = AppConfig(
        host="serenity",
        monitor=MonitorConfig(mode="label_opt_in", health_log_output_limit=6),
    )
    source = FakeSource(
        [
            container(
                id="abc123",
                health="unhealthy",
                labels={
                    "docker-health-alert.enable": "true",
                    "com.docker.compose.project": "gt",
                    "com.docker.compose.service": "qbittorrent",
                    "ApiToken": "secret",
                },
                health_log=HealthLogSnapshot(exit_code=1, output="failure output"),
            ),
        ],
    )

    result = reconcile_startup(
        source,
        config,
        tracker,
        event_time=datetime(2026, 6, 27, 17, 0, tzinfo=UTC),
    )

    assert result.inspected == 1
    assert result.monitored == 1
    assert tracker.current_health("abc123") == "unhealthy"
    assert len(result.alerts) == 1
    alert = result.alerts[0].to_dict()
    assert alert["status"] == "firing"
    assert alert["container"]["previous_health"] is None
    assert alert["compose"] == {"project": "gt", "service": "qbittorrent"}
    assert alert["labels"]["ApiToken"] == "[redacted]"
    assert alert["health_log"] == {"exit_code": 1, "output": "failur"}


def test_reconcile_startup_initializes_healthy_without_alert() -> None:
    tracker = HealthStateTracker()
    config = AppConfig(host="serenity", monitor=MonitorConfig(mode="label_opt_in"))

    result = reconcile_startup(
        FakeSource([container(id="healthy-id", health="healthy")]),
        config,
        tracker,
    )

    assert result.monitored == 1
    assert result.alerts == []
    assert tracker.current_health("healthy-id") == "healthy"


def test_reconcile_startup_starting_alert_depends_on_config() -> None:
    disabled_tracker = HealthStateTracker()
    disabled_config = AppConfig(
        host="serenity",
        monitor=MonitorConfig(mode="label_opt_in", send_starting=False),
    )

    disabled_result = reconcile_startup(
        FakeSource([container(id="starting-id", health="starting")]),
        disabled_config,
        disabled_tracker,
    )

    assert disabled_result.alerts == []
    assert disabled_tracker.current_health("starting-id") == "starting"

    enabled_tracker = HealthStateTracker()
    enabled_config = AppConfig(
        host="serenity",
        monitor=MonitorConfig(mode="label_opt_in", send_starting=True),
    )
    enabled_result = reconcile_startup(
        FakeSource([container(id="starting-id", health="starting")]),
        enabled_config,
        enabled_tracker,
    )

    assert len(enabled_result.alerts) == 1
    assert enabled_result.alerts[0].status == "starting"


def test_reconcile_startup_ignores_unmonitored_and_without_healthcheck() -> None:
    tracker = HealthStateTracker()
    config = AppConfig(host="serenity", monitor=MonitorConfig(mode="label_opt_in"))

    result = reconcile_startup(
        FakeSource(
            [
                container(id="no-health", has_healthcheck=False),
                container(id="not-opted-in", labels={}),
            ],
        ),
        config,
        tracker,
    )

    assert result.inspected == 2
    assert result.ignored_without_healthcheck == 1
    assert result.ignored_unmonitored == 1
    assert result.monitored == 0
    assert result.alerts == []


def test_startup_alert_status_only_emits_unhealthy_and_enabled_starting() -> None:
    assert startup_alert_status("unhealthy") == "firing"
    assert startup_alert_status("healthy") is None
    assert startup_alert_status("starting", send_starting=False) is None
    assert startup_alert_status("starting", send_starting=True) == "starting"
