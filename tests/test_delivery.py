from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from docker_health_alerts.config import ReceiverConfig
from docker_health_alerts.delivery import DeliveryCoordinator, FatalDeliveryError
from docker_health_alerts.plugins import DeliveryResult


class FakeReceiver:
    def __init__(self, name: str, results: list[DeliveryResult]) -> None:
        self.name = name
        self.results = results
        self.calls: list[Mapping[str, Any]] = []

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult:
        self.calls.append(alert)
        if len(self.calls) <= len(self.results):
            return self.results[len(self.calls) - 1]
        return self.results[-1]


class RaisingReceiver:
    name = "raising"

    def __init__(self) -> None:
        self.calls = 0

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult:
        self.calls += 1
        raise TimeoutError("secret webhook https://example.invalid")


def receiver_config(
    name: str,
    *,
    retries: int = 0,
    fatal: bool = False,
) -> ReceiverConfig:
    return ReceiverConfig(
        name=name,
        plugin="generic-webhook",
        config={"retries": retries},
        fatal=fatal,
    )


def test_retryable_failure_retries_until_success() -> None:
    logs: list[dict[str, Any]] = []
    receiver = FakeReceiver(
        "raw-webhook",
        [
            DeliveryResult.retryable_failure("temporary"),
            DeliveryResult.success(),
        ],
    )
    coordinator = DeliveryCoordinator(
        receivers={"raw-webhook": receiver},
        receiver_configs={"raw-webhook": receiver_config("raw-webhook", retries=2)},
        log_event=logs.append,
    )

    outcomes = coordinator.deliver({"status": "firing"}, ["raw-webhook"])

    assert outcomes[0].status == "success"
    assert outcomes[0].attempts == 2
    assert len(receiver.calls) == 2
    assert [log["event"] for log in logs] == [
        "delivery.attempt",
        "delivery.result",
        "delivery.attempt",
        "delivery.result",
    ]


def test_permanent_failure_is_not_retried() -> None:
    receiver = FakeReceiver("raw-webhook", [DeliveryResult.permanent_failure("bad")])
    coordinator = DeliveryCoordinator(
        receivers={"raw-webhook": receiver},
        receiver_configs={"raw-webhook": receiver_config("raw-webhook", retries=3)},
    )

    outcomes = coordinator.deliver({"status": "firing"}, ["raw-webhook"])

    assert outcomes[0].status == "permanent_failure"
    assert outcomes[0].attempts == 1
    assert len(receiver.calls) == 1


def test_receiver_exception_is_retryable_and_does_not_stop_other_receivers() -> None:
    raising = RaisingReceiver()
    success = FakeReceiver("discord", [DeliveryResult.success()])
    coordinator = DeliveryCoordinator(
        receivers={"raising": raising, "discord": success},
        receiver_configs={
            "raising": receiver_config("raising", retries=0),
            "discord": ReceiverConfig(name="discord", plugin="discord"),
        },
    )

    outcomes = coordinator.deliver({"status": "firing"}, ["raising", "discord"])

    assert [outcome.status for outcome in outcomes] == ["retryable_failure", "success"]
    assert raising.calls == 1
    assert len(success.calls) == 1


def test_fatal_receiver_failure_raises_and_stops_delivery() -> None:
    fatal = FakeReceiver("fatal", [DeliveryResult.permanent_failure("bad")])
    next_receiver = FakeReceiver("next", [DeliveryResult.success()])
    coordinator = DeliveryCoordinator(
        receivers={"fatal": fatal, "next": next_receiver},
        receiver_configs={
            "fatal": receiver_config("fatal", fatal=True),
            "next": receiver_config("next"),
        },
    )

    with pytest.raises(FatalDeliveryError, match="fatal"):
        coordinator.deliver({"status": "firing"}, ["fatal", "next"])

    assert len(fatal.calls) == 1
    assert next_receiver.calls == []


def test_delivery_logs_do_not_include_result_message_or_alert_payload() -> None:
    logs: list[dict[str, Any]] = []
    receiver = FakeReceiver(
        "raw-webhook",
        [DeliveryResult.retryable_failure("https://secret.example/webhook")],
    )
    coordinator = DeliveryCoordinator(
        receivers={"raw-webhook": receiver},
        receiver_configs={"raw-webhook": receiver_config("raw-webhook", retries=0)},
        log_event=logs.append,
    )

    coordinator.deliver(
        {"status": "firing", "labels": {"ApiToken": "secret-value"}},
        ["raw-webhook"],
    )

    serialized_logs = repr(logs)
    assert "https://secret.example" not in serialized_logs
    assert "secret-value" not in serialized_logs
    assert logs[-1]["delivery_status"] == "retryable_failure"
