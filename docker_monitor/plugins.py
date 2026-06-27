from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

from docker_monitor.config import ReceiverConfig, is_plugin_reference

DeliveryStatus = Literal["success", "retryable_failure", "permanent_failure"]
PLUGIN_MODULES = {
    "generic-webhook": "docker_monitor.receivers.generic_webhook",
    "discord": "docker_monitor.receivers.discord",
}


@dataclass(frozen=True)
class DeliveryResult:
    status: DeliveryStatus
    message: str = ""
    retry_after_seconds: float | None = None

    @classmethod
    def success(cls, message: str = "delivered") -> DeliveryResult:
        return cls(status="success", message=message)

    @classmethod
    def retryable_failure(cls, message: str = "") -> DeliveryResult:
        return cls(status="retryable_failure", message=message)

    @classmethod
    def permanent_failure(cls, message: str = "") -> DeliveryResult:
        return cls(status="permanent_failure", message=message)


class Receiver(Protocol):
    name: str

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult: ...


class ReceiverFactory(Protocol):
    def create_receiver(
        self,
        name: str,
        config: Mapping[str, Any],
    ) -> Receiver: ...


class PluginLoadError(RuntimeError):
    pass


def load_receivers(
    receiver_configs: list[ReceiverConfig],
) -> dict[str, Receiver]:
    receivers: dict[str, Receiver] = {}
    imported_plugins: dict[str, ReceiverFactory] = {}

    for receiver_config in receiver_configs:
        factory = imported_plugins.get(receiver_config.plugin)
        if factory is None:
            factory = import_receiver_factory(receiver_config.plugin)
            imported_plugins[receiver_config.plugin] = factory
        receivers[receiver_config.name] = factory.create_receiver(
            receiver_config.name,
            receiver_config.config,
        )

    return receivers


def import_receiver_factory(plugin_name: str) -> ReceiverFactory:
    module_name = PLUGIN_MODULES.get(plugin_name)
    if module_name is None and not is_plugin_reference(plugin_name):
        raise PluginLoadError(f"unknown receiver plugin {plugin_name!r}")
    if module_name is None:
        module_name = plugin_name

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise PluginLoadError(
            f"configured receiver plugin {plugin_name!r} is missing",
        ) from exc

    create_receiver = getattr(module, "create_receiver", None)
    if not callable(create_receiver):
        raise PluginLoadError(
            f"configured receiver plugin {plugin_name!r} has no create_receiver",
        )

    return cast(ReceiverFactory, module)
