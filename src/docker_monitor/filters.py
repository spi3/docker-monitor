from __future__ import annotations

from docker_monitor.alerts import ContainerSnapshot, normalize_container_name
from docker_monitor.config import MonitorConfig

COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
COMPOSE_SERVICE_LABEL = "com.docker.compose.service"


def should_monitor_container(
    container: ContainerSnapshot,
    monitor: MonitorConfig,
) -> bool:
    return monitor_mode_allows(container, monitor) and optional_filters_allow(
        container,
        monitor,
    )


def monitor_mode_allows(container: ContainerSnapshot, monitor: MonitorConfig) -> bool:
    label_value = container.labels.get(monitor.label)

    if monitor.mode == "label_opt_in":
        return is_label_true(label_value)

    if monitor.mode == "label_opt_out":
        return not is_label_false(label_value)

    return False


def optional_filters_allow(
    container: ContainerSnapshot,
    monitor: MonitorConfig,
) -> bool:
    filters = monitor.filters
    labels = container.labels

    if filters.names and normalize_container_name(container.name) not in filters.names:
        return False

    if filters.images and not any(
        image_filter_matches(container.image, image_filter)
        for image_filter in filters.images
    ):
        return False

    if (
        filters.compose_projects
        and labels.get(COMPOSE_PROJECT_LABEL) not in filters.compose_projects
    ):
        return False

    if (
        filters.compose_services
        and labels.get(COMPOSE_SERVICE_LABEL) not in filters.compose_services
    ):
        return False

    for label_name, expected_value in filters.labels.items():
        if labels.get(label_name) != expected_value:
            return False

    return True


def is_label_true(value: str | None) -> bool:
    return normalize_label_bool(value) == "true"


def is_label_false(value: str | None) -> bool:
    return normalize_label_bool(value) == "false"


def normalize_label_bool(value: str | None) -> str | None:
    return value.strip().lower() if value is not None else None


def image_filter_matches(image: str, image_filter: str) -> bool:
    return (
        image == image_filter
        or image.startswith(f"{image_filter}:")
        or image.startswith(f"{image_filter}@")
    )
