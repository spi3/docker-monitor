from __future__ import annotations

from dataclasses import dataclass

from docker_health_alerts.alerts import AlertStatus, alert_status_for_health


@dataclass(frozen=True)
class HealthTransition:
    container_id: str
    previous_health: str | None
    current_health: str


@dataclass(frozen=True)
class HealthObservation:
    transition: HealthTransition
    alert_status: AlertStatus | None


class HealthStateTracker:
    def __init__(self) -> None:
        self._health_by_container_id: dict[str, str] = {}

    def current_health(self, container_id: str) -> str | None:
        return self._health_by_container_id.get(container_id)

    def set_initial(self, container_id: str, health: str) -> None:
        self._health_by_container_id[container_id] = health

    def record_transition(
        self,
        container_id: str,
        health: str,
    ) -> HealthTransition | None:
        previous_health = self.current_health(container_id)
        if previous_health == health:
            return None

        self._health_by_container_id[container_id] = health
        return HealthTransition(
            container_id=container_id,
            previous_health=previous_health,
            current_health=health,
        )

    def remove(self, container_id: str) -> None:
        self._health_by_container_id.pop(container_id, None)


def record_health_observation(
    tracker: HealthStateTracker,
    *,
    container_id: str,
    health: str,
    send_resolved: bool = True,
    send_starting: bool = False,
) -> HealthObservation | None:
    transition = tracker.record_transition(container_id, health)
    if transition is None:
        return None

    return HealthObservation(
        transition=transition,
        alert_status=alert_status_for_health(
            health,
            send_resolved=send_resolved,
            send_starting=send_starting,
        ),
    )
