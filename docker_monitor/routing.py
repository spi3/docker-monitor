from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from docker_monitor.alerts import Alert
from docker_monitor.config import RouteConfig

LogEvent = Callable[[dict[str, Any]], None]


def route_alert(
    alert: Alert | Mapping[str, Any],
    routes: list[RouteConfig],
    *,
    log_event: LogEvent | None = None,
) -> list[str]:
    payload = alert_payload(alert)
    receivers: list[str] = []
    seen: set[str] = set()

    for route in routes:
        if not route_matches(route, payload):
            continue
        for receiver_name in route.receivers:
            if receiver_name not in seen:
                receivers.append(receiver_name)
                seen.add(receiver_name)

    if not receivers and log_event is not None:
        log_event(
            {
                "event": "route.unmatched",
                "alert_status": payload.get("status"),
                "alert": payload.get("alert"),
            },
        )

    return receivers


def route_matches(route: RouteConfig, alert: Mapping[str, Any]) -> bool:
    return all(
        get_alert_field(alert, field_path) == expected
        for field_path, expected in route.match.items()
    )


def get_alert_field(alert: Mapping[str, Any], field_path: str) -> Any:
    current: Any = alert
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def alert_payload(alert: Alert | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(alert, Alert):
        return alert.to_dict()
    return dict(alert)
