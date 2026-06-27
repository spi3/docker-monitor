from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from docker_monitor.plugins import DeliveryResult


class DropReceiver:
    def __init__(self, name: str) -> None:
        self.name = name

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult:
        container = alert.get("container", {})
        print(
            json.dumps(
                {
                    "event": "mock_receiver.alert_received",
                    "receiver": self.name,
                    "status": alert.get("status"),
                    "alert": alert.get("alert"),
                    "container": container.get("name")
                    if isinstance(container, Mapping)
                    else None,
                    "health": container.get("health")
                    if isinstance(container, Mapping)
                    else None,
                    "previous_health": container.get("previous_health")
                    if isinstance(container, Mapping)
                    else None,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return DeliveryResult.success("dropped")


def create_receiver(name: str, config: Mapping[str, Any]) -> DropReceiver:
    return DropReceiver(name)
