from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import docker  # type: ignore[import-untyped]
from docker.errors import NotFound  # type: ignore[import-untyped]

from docker_health_alerts.alerts import ContainerSnapshot, HealthLogSnapshot

DOCKER_EVENT_FILTERS = {"type": "container", "event": "health_status"}


@dataclass(frozen=True)
class DockerHealthEvent:
    container_id: str
    health: str
    time: datetime


class DockerSource:
    def __init__(self, client: Any | None = None, base_url: str | None = None) -> None:
        if client is not None:
            self._client = client
        elif base_url is not None:
            self._client = docker.DockerClient(base_url=base_url)
        else:
            self._client = docker.from_env()

    def list_containers(self) -> list[ContainerSnapshot]:
        snapshots: list[ContainerSnapshot] = []
        for container in self._client.containers.list(all=True):
            container.reload()
            snapshots.append(snapshot_from_container_attrs(container.attrs))
        return snapshots

    def inspect_container(self, container_id: str) -> ContainerSnapshot | None:
        try:
            container = self._client.containers.get(container_id)
        except NotFound:
            return None
        container.reload()
        return snapshot_from_container_attrs(container.attrs)

    def stream_health_events(self) -> Iterator[DockerHealthEvent]:
        for event in self._client.events(decode=True, filters=DOCKER_EVENT_FILTERS):
            parsed = parse_health_status_event(event)
            if parsed is not None:
                yield parsed


def snapshot_from_container_attrs(attrs: Mapping[str, Any]) -> ContainerSnapshot:
    config = mapping_value(attrs, "Config")
    state = mapping_value(attrs, "State")
    health_state = mapping_value(state, "Health")

    return ContainerSnapshot(
        id=str(attrs.get("Id", "")),
        name=str(attrs.get("Name", "")),
        image=str(config.get("Image") or attrs.get("Image", "")),
        state=str(state.get("Status", "")),
        health=str(health_state.get("Status", "none")),
        labels=string_mapping(config.get("Labels")),
        health_log=latest_health_log(health_state),
        has_healthcheck=container_has_healthcheck(attrs),
    )


def container_has_healthcheck(attrs: Mapping[str, Any]) -> bool:
    config = mapping_value(attrs, "Config")
    state = mapping_value(attrs, "State")
    health_state = mapping_value(state, "Health")
    if health_state:
        return True

    healthcheck = mapping_value(config, "Healthcheck")
    if not healthcheck:
        return False

    test = healthcheck.get("Test")
    if not isinstance(test, list) or not test:
        return False

    return not (len(test) == 1 and str(test[0]).upper() == "NONE")


def latest_health_log(health_state: Mapping[str, Any]) -> HealthLogSnapshot | None:
    log_entries = health_state.get("Log")
    if not isinstance(log_entries, list) or not log_entries:
        return None

    latest_entry = log_entries[-1]
    if not isinstance(latest_entry, Mapping):
        return None

    exit_code = latest_entry.get("ExitCode")
    return HealthLogSnapshot(
        exit_code=exit_code if isinstance(exit_code, int) else None,
        output=str(latest_entry.get("Output", "")),
    )


def parse_health_status_event(event: Mapping[str, Any]) -> DockerHealthEvent | None:
    container_id = event.get("id")
    if not isinstance(container_id, str) or not container_id:
        actor = mapping_value(event, "Actor")
        container_id = actor.get("ID")

    health = health_from_event(event)
    if not isinstance(container_id, str) or not container_id or health is None:
        return None

    return DockerHealthEvent(
        container_id=container_id,
        health=health,
        time=event_time(event),
    )


def health_from_event(event: Mapping[str, Any]) -> str | None:
    actor = mapping_value(event, "Actor")
    attributes = mapping_value(actor, "Attributes")
    health = attributes.get("health_status")
    if isinstance(health, str) and health:
        return health

    status = event.get("status")
    if isinstance(status, str) and status.startswith("health_status:"):
        return status.split(":", maxsplit=1)[1].strip()

    return None


def event_time(event: Mapping[str, Any]) -> datetime:
    time_nano = event.get("timeNano")
    if isinstance(time_nano, int):
        return datetime.fromtimestamp(time_nano / 1_000_000_000, tz=UTC)

    time_seconds = event.get("time")
    if isinstance(time_seconds, int | float):
        return datetime.fromtimestamp(float(time_seconds), tz=UTC)

    return datetime.now(UTC)


def mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(item_key): str(item_value)
        for item_key, item_value in value.items()
        if item_value is not None
    }
