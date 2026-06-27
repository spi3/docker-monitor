from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from docker_monitor.alerts import Alert
from docker_monitor.config import ReceiverConfig
from docker_monitor.plugins import DeliveryResult, DeliveryStatus, Receiver
from docker_monitor.routing import alert_payload

LogEvent = Callable[[dict[str, Any]], None]


class FatalDeliveryError(RuntimeError):
    def __init__(self, receiver_name: str, result: DeliveryResult) -> None:
        super().__init__(
            f"fatal delivery failure for receiver {receiver_name!r}: {result.status}"
        )
        self.receiver_name = receiver_name
        self.result = result


@dataclass(frozen=True)
class DeliveryOutcome:
    receiver_name: str
    status: DeliveryStatus
    attempts: int
    fatal: bool = False


class DeliveryCoordinator:
    def __init__(
        self,
        *,
        receivers: Mapping[str, Receiver],
        receiver_configs: Mapping[str, ReceiverConfig],
        log_event: LogEvent | None = None,
        default_retries: int = 3,
    ) -> None:
        self._receivers = receivers
        self._receiver_configs = receiver_configs
        self._log_event = log_event
        self._default_retries = default_retries

    def deliver(
        self,
        alert: Alert | Mapping[str, Any],
        receiver_names: list[str],
    ) -> list[DeliveryOutcome]:
        payload = alert_payload(alert)
        outcomes: list[DeliveryOutcome] = []

        for receiver_name in receiver_names:
            outcome = self._deliver_to_receiver(payload, receiver_name)
            outcomes.append(outcome)
            if outcome.fatal and outcome.status != "success":
                result = DeliveryResult(status=outcome.status)
                raise FatalDeliveryError(receiver_name, result)

        return outcomes

    def _deliver_to_receiver(
        self,
        alert: Mapping[str, Any],
        receiver_name: str,
    ) -> DeliveryOutcome:
        receiver = self._receivers[receiver_name]
        receiver_config = self._receiver_configs[receiver_name]
        max_attempts = configured_retries(receiver_config, self._default_retries) + 1
        final_result = DeliveryResult.permanent_failure("not attempted")

        for attempt in range(1, max_attempts + 1):
            self._log(
                {
                    "event": "delivery.attempt",
                    "receiver": receiver_name,
                    "attempt": attempt,
                },
            )
            final_result = safe_deliver(receiver, alert)
            self._log(
                {
                    "event": "delivery.result",
                    "receiver": receiver_name,
                    "delivery_status": final_result.status,
                    "attempt": attempt,
                },
            )

            if final_result.status in {"success", "permanent_failure"}:
                break

        return DeliveryOutcome(
            receiver_name=receiver_name,
            status=final_result.status,
            attempts=attempt,
            fatal=receiver_config.fatal,
        )

    def _log(self, event: dict[str, Any]) -> None:
        if self._log_event is not None:
            self._log_event(event)


def safe_deliver(receiver: Receiver, alert: Mapping[str, Any]) -> DeliveryResult:
    try:
        return receiver.deliver(alert)
    except Exception as exc:  # noqa: BLE001
        return DeliveryResult.retryable_failure(exc.__class__.__name__)


def configured_retries(receiver_config: ReceiverConfig, default_retries: int) -> int:
    raw_retries = receiver_config.config.get("retries", default_retries)
    if isinstance(raw_retries, bool):
        return default_retries
    if isinstance(raw_retries, int):
        return max(raw_retries, 0)
    return default_retries
