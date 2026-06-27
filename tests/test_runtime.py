from __future__ import annotations

import io
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from docker_monitor.alerts import ContainerSnapshot
from docker_monitor.config import (
    AppConfig,
    MonitorConfig,
    ReceiverConfig,
    RouteConfig,
)
from docker_monitor.docker_source import DockerHealthEvent
from docker_monitor.plugins import DeliveryResult
from docker_monitor.runtime import RuntimeSettings, ServiceRuntime
from docker_monitor.structured_logging import JsonLogger


@dataclass
class FakeSource:
    containers_by_cycle: list[list[ContainerSnapshot]]
    events_by_cycle: list[list[DockerHealthEvent] | Exception]
    inspected: dict[str, ContainerSnapshot] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    list_calls: int = 0
    stream_calls: int = 0

    def list_containers(self) -> list[ContainerSnapshot]:
        self.calls.append("list_containers")
        index = min(self.list_calls, len(self.containers_by_cycle) - 1)
        self.list_calls += 1
        return self.containers_by_cycle[index]

    def inspect_container(self, container_id: str) -> ContainerSnapshot | None:
        self.calls.append(f"inspect:{container_id}")
        return self.inspected.get(container_id)

    def stream_health_events(self) -> Iterator[DockerHealthEvent]:
        self.calls.append("stream_health_events")
        index = min(self.stream_calls, len(self.events_by_cycle) - 1)
        self.stream_calls += 1
        events = self.events_by_cycle[index]
        if isinstance(events, Exception):
            raise events
        yield from events


class FakeReceiver:
    def __init__(self, name: str = "raw-webhook") -> None:
        self.name = name
        self.alerts: list[Mapping[str, Any]] = []

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult:
        self.alerts.append(alert)
        return DeliveryResult.success()


def container(
    *,
    id: str = "container-id",
    health: str = "healthy",
    has_healthcheck: bool = True,
    labels: dict[str, str] | None = None,
) -> ContainerSnapshot:
    return ContainerSnapshot(
        id=id,
        name="qbittorrent",
        image="lscr.io/linuxserver/qbittorrent:latest",
        state="running",
        health=health,
        labels=labels if labels is not None else {"docker-monitor.enable": "true"},
        has_healthcheck=has_healthcheck,
    )


def event(container_id: str, health: str) -> DockerHealthEvent:
    return DockerHealthEvent(
        container_id=container_id,
        health=health,
        time=datetime(2026, 6, 27, 17, 0, tzinfo=UTC),
    )


def config(*, send_resolved: bool = True, send_starting: bool = False) -> AppConfig:
    return AppConfig(
        host="serenity",
        monitor=MonitorConfig(
            mode="label_opt_in",
            send_resolved=send_resolved,
            send_starting=send_starting,
        ),
        receivers=[
            ReceiverConfig(
                name="raw-webhook",
                plugin="generic-webhook",
                config={"url": "https://example.invalid/webhook"},
            ),
        ],
        routes=[RouteConfig(match={"severity": "warning"}, receivers=["raw-webhook"])],
    )


def runtime(
    source: FakeSource,
    receiver: FakeReceiver,
    *,
    stream: io.StringIO | None = None,
) -> ServiceRuntime:
    app_config = config()
    return ServiceRuntime(
        config=app_config,
        source=source,
        receivers={"raw-webhook": receiver},
        receiver_configs={receiver.name: app_config.receivers[0]},
        logger=JsonLogger(stream),
        settings=RuntimeSettings(reconnect_backoff_seconds=0, shutdown_grace_seconds=2),
        sleep=lambda seconds: None,
    )


def test_startup_reconciliation_runs_before_stream_and_delivers_alert() -> None:
    receiver = FakeReceiver()
    source = FakeSource(
        containers_by_cycle=[[container(id="unhealthy-id", health="unhealthy")]],
        events_by_cycle=[[]],
    )

    exit_code = runtime(source, receiver).run(max_reconnects=0)

    assert exit_code == 0
    assert source.calls[:2] == ["list_containers", "stream_health_events"]
    assert len(receiver.alerts) == 1
    assert receiver.alerts[0]["status"] == "firing"
    assert receiver.alerts[0]["container"]["id"] == "unhealthy-id"


def test_live_event_transition_routes_alert_after_startup_state_init() -> None:
    receiver = FakeReceiver()
    unhealthy = container(id="abc123", health="unhealthy")
    source = FakeSource(
        containers_by_cycle=[[container(id="abc123", health="healthy")]],
        events_by_cycle=[[event("abc123", "unhealthy")]],
        inspected={"abc123": unhealthy},
    )

    exit_code = runtime(source, receiver).run(max_reconnects=0)

    assert exit_code == 0
    assert len(receiver.alerts) == 1
    assert receiver.alerts[0]["status"] == "firing"
    assert receiver.alerts[0]["container"]["previous_health"] == "healthy"


def test_stream_disconnect_reconnects_and_reconciles_again() -> None:
    receiver = FakeReceiver()
    source = FakeSource(
        containers_by_cycle=[
            [container(id="abc123", health="healthy")],
            [container(id="abc123", health="healthy")],
        ],
        events_by_cycle=[RuntimeError("disconnect"), []],
    )

    exit_code = runtime(source, receiver).run(max_reconnects=1)

    assert exit_code == 0
    assert source.list_calls == 2
    assert source.stream_calls == 2


def test_stream_disconnect_returns_failure_after_reconnect_limit() -> None:
    receiver = FakeReceiver()
    source = FakeSource(
        containers_by_cycle=[[container(id="abc123", health="healthy")]],
        events_by_cycle=[RuntimeError("disconnect")],
    )

    exit_code = runtime(source, receiver).run(max_reconnects=0)

    assert exit_code == 1


def test_request_shutdown_sets_flag_and_logs_grace_period() -> None:
    receiver = FakeReceiver()
    stream = io.StringIO()
    service = runtime(
        FakeSource(containers_by_cycle=[[]], events_by_cycle=[[]]),
        receiver,
        stream=stream,
    )

    service.request_shutdown()

    assert service.shutdown_requested
    record = json.loads(stream.getvalue().splitlines()[0])
    assert record["event"] == "service.shutdown_requested"
    assert record["shutdown_grace_seconds"] == 2


def test_json_logger_writes_structured_json_to_stdout_stream() -> None:
    stream = io.StringIO()
    logger = JsonLogger(stream)

    logger.info("test.event", receiver="raw-webhook", attempt=1)

    record = json.loads(stream.getvalue())
    assert record["level"] == "info"
    assert record["event"] == "test.event"
    assert record["receiver"] == "raw-webhook"
    assert record["attempt"] == 1
    assert "time" in record
