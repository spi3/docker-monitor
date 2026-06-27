from __future__ import annotations

import types
from collections.abc import Mapping
from typing import Any

import pytest

import docker_monitor.plugins as plugin_registry
from docker_monitor.config import ReceiverConfig
from docker_monitor.plugins import (
    DeliveryResult,
    PluginLoadError,
    Receiver,
    import_receiver_factory,
    load_receivers,
)


class FakeReceiver:
    def __init__(self, name: str) -> None:
        self.name = name

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult:
        return DeliveryResult.success()


def test_load_receivers_imports_only_configured_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported_modules: list[str] = []

    fake_module = types.ModuleType("fake_generic_webhook")

    def create_receiver(name: str, config: Mapping[str, Any]) -> Receiver:
        return FakeReceiver(name)

    fake_module.create_receiver = create_receiver  # type: ignore[attr-defined]

    def fake_import_module(module_name: str) -> types.ModuleType:
        imported_modules.append(module_name)
        return fake_module

    monkeypatch.setattr(
        "docker_monitor.plugins.importlib.import_module", fake_import_module
    )

    assert load_receivers([]) == {}

    receivers = load_receivers(
        [
            ReceiverConfig(
                name="raw-webhook",
                plugin="generic-webhook",
                config={"url": "https://example.invalid/webhook"},
            ),
        ],
    )

    assert list(receivers) == ["raw-webhook"]
    assert imported_modules == ["docker_monitor.receivers.generic_webhook"]


def test_load_receivers_imports_each_configured_plugin_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported_modules: list[str] = []
    fake_module = types.ModuleType("fake_generic_webhook")

    def create_receiver(name: str, config: Mapping[str, Any]) -> Receiver:
        return FakeReceiver(name)

    fake_module.create_receiver = create_receiver  # type: ignore[attr-defined]

    def fake_import_module(module_name: str) -> types.ModuleType:
        imported_modules.append(module_name)
        return fake_module

    monkeypatch.setattr(
        "docker_monitor.plugins.importlib.import_module", fake_import_module
    )

    load_receivers(
        [
            ReceiverConfig(
                name="first",
                plugin="generic-webhook",
                config={"url": "https://example.invalid/first"},
            ),
            ReceiverConfig(
                name="second",
                plugin="generic-webhook",
                config={"url": "https://example.invalid/second"},
            ),
        ],
    )

    assert imported_modules == ["docker_monitor.receivers.generic_webhook"]


def test_missing_configured_plugin_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        plugin_registry.PLUGIN_MODULES,
        "missing-plugin",
        "docker_monitor.receivers.missing_plugin",
    )

    with pytest.raises(
        PluginLoadError, match="configured receiver plugin 'missing-plugin' is missing"
    ):
        import_receiver_factory("missing-plugin")
