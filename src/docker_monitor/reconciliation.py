from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from docker_monitor.alerts import (
    Alert,
    AlertStatus,
    ContainerSnapshot,
    build_alert,
)
from docker_monitor.config import AppConfig
from docker_monitor.filters import should_monitor_container
from docker_monitor.state import HealthStateTracker


class ContainerSource(Protocol):
    def list_containers(self) -> list[ContainerSnapshot]: ...


@dataclass(frozen=True)
class StartupReconciliationResult:
    inspected: int = 0
    ignored_not_running: int = 0
    monitored: int = 0
    ignored_without_healthcheck: int = 0
    ignored_unmonitored: int = 0
    alerts: list[Alert] = field(default_factory=list)


def reconcile_startup(
    source: ContainerSource,
    config: AppConfig,
    tracker: HealthStateTracker,
    *,
    event_time: datetime | None = None,
) -> StartupReconciliationResult:
    inspected = 0
    ignored_not_running = 0
    monitored = 0
    ignored_without_healthcheck = 0
    ignored_unmonitored = 0
    alerts: list[Alert] = []

    for container in source.list_containers():
        inspected += 1

        if not is_running_container(container):
            ignored_not_running += 1
            continue

        if not container.has_healthcheck:
            ignored_without_healthcheck += 1
            continue

        if not should_monitor_container(container, config.monitor):
            ignored_unmonitored += 1
            continue

        monitored += 1
        tracker.set_initial(container.id, container.health)

        startup_status = startup_alert_status(
            container.health,
            send_starting=config.monitor.send_starting,
        )
        if startup_status is None:
            continue

        alerts.append(
            build_alert(
                status=startup_status,
                host=config.host,
                severity=config.severity,
                container=container,
                previous_health=None,
                event_time=event_time,
                health_log_output_limit=config.monitor.health_log_output_limit,
            ),
        )

    return StartupReconciliationResult(
        inspected=inspected,
        ignored_not_running=ignored_not_running,
        monitored=monitored,
        ignored_without_healthcheck=ignored_without_healthcheck,
        ignored_unmonitored=ignored_unmonitored,
        alerts=alerts,
    )


def is_running_container(container: ContainerSnapshot) -> bool:
    return container.state.strip().lower() == "running"


def startup_alert_status(
    health: str,
    *,
    send_starting: bool = False,
) -> AlertStatus | None:
    normalized_health = health.strip().lower()
    if normalized_health == "unhealthy":
        return "firing"
    if normalized_health == "starting" and send_starting:
        return "starting"
    return None
