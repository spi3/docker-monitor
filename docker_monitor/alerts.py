from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ALERT_SCHEMA_VERSION = "1"
DEFAULT_ALERT_NAME = "DockerContainerUnhealthy"
DEFAULT_SEVERITY = "warning"
REDACTED_VALUE = "[redacted]"

AlertStatus = Literal["firing", "resolved", "starting"]
DockerHealthStatus = Literal["healthy", "unhealthy", "starting"]

SENSITIVE_LABEL_TOKENS = (
    "password",
    "passwd",
    "secret",
    "token",
    "key",
    "credential",
    "authorization",
    "auth",
)


@dataclass(frozen=True)
class HealthLogSnapshot:
    exit_code: int | None = None
    output: str | None = None


@dataclass(frozen=True)
class ContainerSnapshot:
    id: str
    name: str
    image: str
    state: str
    health: str
    labels: Mapping[str, str] = field(default_factory=dict)
    health_log: HealthLogSnapshot | None = None
    has_healthcheck: bool = True


class ContainerAlertDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    image: str
    state: str
    health: str
    previous_health: str | None


class ComposeAlertDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str | None = None
    service: str | None = None


class EventDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = "docker"
    time: str


class HealthLogDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exit_code: int | None = None
    output: str | None = None


class Alert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = ALERT_SCHEMA_VERSION
    status: AlertStatus
    alert: str = DEFAULT_ALERT_NAME
    host: str
    severity: str = DEFAULT_SEVERITY
    container: ContainerAlertDetails
    compose: ComposeAlertDetails
    labels: dict[str, str]
    event: EventDetails
    health_log: HealthLogDetails

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def alert_status_for_health(
    health: str,
    *,
    send_resolved: bool = True,
    send_starting: bool = False,
) -> AlertStatus | None:
    normalized_health = health.strip().lower()
    if normalized_health == "unhealthy":
        return "firing"
    if normalized_health == "healthy" and send_resolved:
        return "resolved"
    if normalized_health == "starting" and send_starting:
        return "starting"
    return None


def redact_labels(labels: Mapping[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in labels.items():
        if is_sensitive_label_key(key):
            redacted[key] = REDACTED_VALUE
        else:
            redacted[key] = value
    return redacted


def is_sensitive_label_key(key: str) -> bool:
    normalized_key = key.lower()
    return any(token in normalized_key for token in SENSITIVE_LABEL_TOKENS)


def truncate_health_output(output: str | None, limit: int) -> str | None:
    if output is None:
        return None
    if limit <= 0:
        return ""
    return output[:limit]


def build_alert(
    *,
    status: AlertStatus,
    host: str,
    container: ContainerSnapshot,
    previous_health: str | None,
    event_time: datetime | None = None,
    severity: str = DEFAULT_SEVERITY,
    health_log_output_limit: int = 1000,
) -> Alert:
    health_log = container.health_log or HealthLogSnapshot()
    labels = dict(container.labels)

    return Alert(
        status=status,
        host=host,
        severity=severity,
        container=ContainerAlertDetails(
            id=container.id,
            name=normalize_container_name(container.name),
            image=container.image,
            state=container.state,
            health=container.health,
            previous_health=previous_health,
        ),
        compose=ComposeAlertDetails(
            project=labels.get("com.docker.compose.project"),
            service=labels.get("com.docker.compose.service"),
        ),
        labels=redact_labels(labels),
        event=EventDetails(time=format_event_time(event_time)),
        health_log=HealthLogDetails(
            exit_code=health_log.exit_code,
            output=truncate_health_output(
                health_log.output,
                health_log_output_limit,
            ),
        ),
    )


def normalize_container_name(name: str) -> str:
    return name[1:] if name.startswith("/") else name


def format_event_time(event_time: datetime | None = None) -> str:
    timestamp = event_time or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
