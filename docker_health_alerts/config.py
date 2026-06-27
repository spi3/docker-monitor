from __future__ import annotations

import os
import re
import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CONFIG_FILE_ENV = "CONFIG_FILE"
DEFAULT_CONFIG_FILE = "/config/config.yaml"
DEFAULT_MONITOR_LABEL = "docker-health-alert.enable"
KNOWN_PLUGIN_NAMES = frozenset({"discord", "generic-webhook"})

DurationInput = str | int | float
MonitorMode = Literal["label_opt_in", "label_opt_out"]

_DURATION_RE = re.compile(
    r"^\s*(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>ms|s|m|h)?\s*$",
    re.IGNORECASE,
)
_DURATION_MULTIPLIERS = {
    None: 1.0,
    "ms": 0.001,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
}
_INLINE_SECRET_PAIRS = (
    ("url", "url_file"),
    ("webhook_url", "webhook_url_file"),
    ("WEBHOOK_URL", "WEBHOOK_URL_FILE"),
)


class ConfigError(ValueError):
    """Raised when configuration cannot be loaded or validated."""


class MonitorFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    names: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    compose_projects: list[str] = Field(default_factory=list)
    compose_services: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)


class MonitorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: MonitorMode = "label_opt_in"
    label: str = DEFAULT_MONITOR_LABEL
    send_resolved: bool = True
    send_starting: bool = False
    health_log_output_limit: int = 1000
    filters: MonitorFilters = Field(default_factory=MonitorFilters)

    @model_validator(mode="after")
    def validate_health_log_output_limit(self) -> Self:
        if self.health_log_output_limit < 0:
            raise ValueError("monitor.health_log_output_limit must be >= 0")
        return self


class ReceiverConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    config: dict[str, Any] = Field(default_factory=dict)
    fatal: bool = False

    @model_validator(mode="after")
    def validate_receiver(self) -> Self:
        if self.plugin not in KNOWN_PLUGIN_NAMES:
            known = ", ".join(sorted(KNOWN_PLUGIN_NAMES))
            raise ValueError(f"unknown plugin {self.plugin!r}; known plugins: {known}")
        self.config = normalize_receiver_config(self.name, self.config)
        return self


class RouteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match: dict[str, str | int | float | bool] = Field(default_factory=dict)
    receivers: list[str]

    @model_validator(mode="after")
    def validate_receivers(self) -> Self:
        if not self.receivers:
            raise ValueError("route receivers must not be empty")
        return self


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(default_factory=socket.gethostname)
    severity: str = "warning"
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    receivers: list[ReceiverConfig] = Field(default_factory=list)
    routes: list[RouteConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        receiver_names: set[str] = set()
        duplicates: set[str] = set()
        for receiver in self.receivers:
            if receiver.name in receiver_names:
                duplicates.add(receiver.name)
            receiver_names.add(receiver.name)

        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            raise ValueError(f"duplicate receiver names: {duplicate_list}")

        unknown_route_receivers = sorted(
            {
                receiver_name
                for route in self.routes
                for receiver_name in route.receivers
                if receiver_name not in receiver_names
            },
        )
        if unknown_route_receivers:
            unknown_list = ", ".join(unknown_route_receivers)
            raise ValueError(f"routes reference unknown receivers: {unknown_list}")

        return self


def parse_duration(value: DurationInput) -> float:
    if isinstance(value, bool):
        raise ValueError("duration must be a number or duration string")

    if isinstance(value, int | float):
        seconds = float(value)
        if seconds <= 0:
            raise ValueError("duration must be greater than zero")
        return seconds

    match = _DURATION_RE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid duration {value!r}")

    unit = match.group("unit")
    normalized_unit = unit.lower() if unit else None
    seconds = float(match.group("value")) * _DURATION_MULTIPLIERS[normalized_unit]
    if seconds <= 0:
        raise ValueError("duration must be greater than zero")
    return seconds


def normalize_receiver_config(
    receiver_name: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = dict(config)

    for inline_key, file_key in _INLINE_SECRET_PAIRS:
        if normalized.get(inline_key) and normalized.get(file_key):
            raise ValueError(
                f"receiver {receiver_name!r} must configure either "
                f"{inline_key!r} or {file_key!r}, not both",
            )

    if "timeout" in normalized:
        normalized["timeout"] = parse_duration_value("timeout", normalized["timeout"])

    validate_secret_file_references(receiver_name, normalized)
    return normalized


def parse_duration_value(field_name: str, value: object) -> float:
    if not isinstance(value, str | int | float) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number or duration string")
    try:
        return parse_duration(value)
    except ValueError as exc:
        raise ValueError(f"{field_name}: {exc}") from exc


def validate_secret_file_references(
    receiver_name: str,
    config: Mapping[str, Any],
) -> None:
    for field_name, path in iter_secret_file_references(config):
        validate_secret_file(receiver_name, field_name, path)


def iter_secret_file_references(
    config: Mapping[str, Any],
) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    for key, value in config.items():
        if key == "header_files":
            if not isinstance(value, Mapping):
                raise ValueError(
                    "header_files must be a mapping of header names to paths"
                )
            for header_name, header_path in value.items():
                if not isinstance(header_name, str) or not isinstance(header_path, str):
                    raise ValueError(
                        "header_files must map string header names to paths"
                    )
                references.append((f"header_files.{header_name}", header_path))
            continue

        if key.lower().endswith("_file"):
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a file path string")
            references.append((key, value))

    return references


def validate_secret_file(receiver_name: str, field_name: str, path: str) -> None:
    if not path.strip():
        raise ValueError(f"receiver {receiver_name!r} {field_name} must not be empty")

    try:
        with Path(path).open("r", encoding="utf-8"):
            pass
    except OSError as exc:
        raise ValueError(
            f"receiver {receiver_name!r} {field_name} is not readable: {path}",
        ) from exc


def load_config_from_env(
    env: Mapping[str, str] | None = None,
) -> AppConfig:
    source_env = os.environ if env is None else env
    return load_config_file(source_env.get(CONFIG_FILE_ENV, DEFAULT_CONFIG_FILE))


def load_config_file(path: str | Path) -> AppConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read config file {config_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"cannot parse config file {config_path}: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ConfigError(f"config file {config_path} must contain a YAML mapping")

    try:
        return AppConfig.model_validate(dict(raw))
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc
