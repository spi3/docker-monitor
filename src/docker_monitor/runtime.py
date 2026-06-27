from __future__ import annotations

import signal
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from docker_monitor.alerts import Alert, build_alert
from docker_monitor.config import AppConfig, ReceiverConfig
from docker_monitor.delivery import DeliveryCoordinator, FatalDeliveryError
from docker_monitor.docker_source import DockerHealthEvent, DockerSource
from docker_monitor.filters import should_monitor_container
from docker_monitor.plugins import Receiver, load_receivers
from docker_monitor.reconciliation import ContainerSource, reconcile_startup
from docker_monitor.routing import route_alert
from docker_monitor.state import HealthStateTracker, record_health_observation
from docker_monitor.structured_logging import JsonLogger


class RuntimeSource(ContainerSource, Protocol):
    def inspect_container(self, container_id: str) -> Any: ...

    def stream_health_events(self) -> Iterator[DockerHealthEvent]: ...


@dataclass(frozen=True)
class RuntimeSettings:
    reconnect_backoff_seconds: float = 1.0
    shutdown_grace_seconds: float = 10.0


class ServiceRuntime:
    def __init__(
        self,
        *,
        config: AppConfig,
        source: RuntimeSource,
        receivers: Mapping[str, Receiver] | None = None,
        receiver_configs: Mapping[str, ReceiverConfig] | None = None,
        tracker: HealthStateTracker | None = None,
        logger: JsonLogger | None = None,
        settings: RuntimeSettings | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.source = source
        self.tracker = tracker or HealthStateTracker()
        self.logger = logger or JsonLogger()
        self.settings = settings or RuntimeSettings()
        self._sleep = sleep
        self._shutdown_requested = False

        self.receiver_configs = (
            receiver_configs
            if receiver_configs is not None
            else {receiver.name: receiver for receiver in config.receivers}
        )
        self.receivers = (
            receivers if receivers is not None else load_receivers(config.receivers)
        )
        self.delivery = DeliveryCoordinator(
            receivers=self.receivers,
            receiver_configs=self.receiver_configs,
            log_event=self._log_delivery_event,
        )

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def request_shutdown(self) -> None:
        self._shutdown_requested = True
        self.logger.info(
            "service.shutdown_requested",
            shutdown_grace_seconds=self.settings.shutdown_grace_seconds,
        )

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, frame: object | None) -> None:
        self.request_shutdown()
        self.logger.info("service.signal", signal=signal.Signals(signum).name)

    def run(self, *, max_reconnects: int | None = None) -> int:
        reconnects = 0
        self.logger.info("service.starting")

        while not self.shutdown_requested:
            self.reconcile_and_deliver()

            try:
                self.consume_events_until_disconnect()
                break
            except Exception as exc:  # noqa: BLE001
                if self.shutdown_requested:
                    break
                self.logger.warning(
                    "docker.stream_disconnected",
                    error=exc.__class__.__name__,
                )
                if max_reconnects is not None and reconnects >= max_reconnects:
                    return 1
                reconnects += 1
                self._sleep(self.settings.reconnect_backoff_seconds)

        self.logger.info("service.stopped")
        return 0

    def reconcile_and_deliver(self) -> None:
        result = reconcile_startup(self.source, self.config, self.tracker)
        self.logger.info(
            "startup.reconciled",
            inspected=result.inspected,
            monitored=result.monitored,
            ignored_without_healthcheck=result.ignored_without_healthcheck,
            ignored_unmonitored=result.ignored_unmonitored,
            alerts=len(result.alerts),
        )
        for alert in result.alerts:
            self.route_and_deliver(alert)

    def consume_events_until_disconnect(self) -> None:
        for event in self.source.stream_health_events():
            if self.shutdown_requested:
                break
            self.process_health_event(event)

    def process_health_event(self, event: DockerHealthEvent) -> None:
        container = self.source.inspect_container(event.container_id)
        if container is None:
            self.logger.info(
                "docker.container_missing", container_id=event.container_id
            )
            return
        if not container.has_healthcheck:
            self.logger.debug(
                "docker.container_without_healthcheck",
                container_id=container.id,
            )
            return
        if not should_monitor_container(container, self.config.monitor):
            self.logger.debug("docker.container_unmonitored", container_id=container.id)
            return

        observation = record_health_observation(
            self.tracker,
            container_id=container.id,
            health=event.health,
            send_resolved=self.config.monitor.send_resolved,
            send_starting=self.config.monitor.send_starting,
        )
        if observation is None:
            self.logger.debug("health.unchanged", container_id=container.id)
            return
        if observation.alert_status is None:
            self.logger.debug(
                "health.changed_without_alert",
                container_id=container.id,
                health=event.health,
            )
            return

        alert = build_alert(
            status=observation.alert_status,
            host=self.config.host,
            severity=self.config.severity,
            container=container,
            previous_health=observation.transition.previous_health,
            event_time=event.time,
            health_log_output_limit=self.config.monitor.health_log_output_limit,
        )
        self.route_and_deliver(alert)

    def route_and_deliver(self, alert: Alert) -> None:
        receiver_names = route_alert(
            alert,
            self.config.routes,
            log_event=self._log_route_event,
        )
        if not receiver_names:
            return

        try:
            self.delivery.deliver(alert, receiver_names)
        except FatalDeliveryError as exc:
            self.logger.error(
                "delivery.fatal",
                receiver=exc.receiver_name,
                delivery_status=exc.result.status,
            )
            self.request_shutdown()

    def _log_route_event(self, event: dict[str, Any]) -> None:
        self.logger.info(str(event.pop("event")), **event)

    def _log_delivery_event(self, event: dict[str, Any]) -> None:
        self.logger.info(str(event.pop("event")), **event)


def build_runtime_from_config(
    config: AppConfig,
    *,
    logger: JsonLogger | None = None,
) -> ServiceRuntime:
    return ServiceRuntime(config=config, source=DockerSource(), logger=logger)
