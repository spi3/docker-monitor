from __future__ import annotations

from docker_monitor.state import HealthStateTracker, record_health_observation


def test_unknown_to_unhealthy_emits_firing_and_records_state() -> None:
    tracker = HealthStateTracker()

    observation = record_health_observation(
        tracker,
        container_id="full-container-id",
        health="unhealthy",
    )

    assert observation is not None
    assert observation.transition.previous_health is None
    assert observation.transition.current_health == "unhealthy"
    assert observation.alert_status == "firing"
    assert tracker.current_health("full-container-id") == "unhealthy"


def test_unchanged_health_is_suppressed() -> None:
    tracker = HealthStateTracker()
    tracker.set_initial("container-id", "unhealthy")

    assert (
        record_health_observation(
            tracker,
            container_id="container-id",
            health="unhealthy",
        )
        is None
    )


def test_unhealthy_to_healthy_emits_resolved_when_enabled() -> None:
    tracker = HealthStateTracker()
    tracker.set_initial("container-id", "unhealthy")

    observation = record_health_observation(
        tracker,
        container_id="container-id",
        health="healthy",
        send_resolved=True,
    )

    assert observation is not None
    assert observation.transition.previous_health == "unhealthy"
    assert observation.alert_status == "resolved"
    assert tracker.current_health("container-id") == "healthy"


def test_disabled_resolved_still_updates_state_without_alert() -> None:
    tracker = HealthStateTracker()
    tracker.set_initial("container-id", "unhealthy")

    observation = record_health_observation(
        tracker,
        container_id="container-id",
        health="healthy",
        send_resolved=False,
    )

    assert observation is not None
    assert observation.alert_status is None
    assert tracker.current_health("container-id") == "healthy"


def test_starting_alert_depends_on_send_starting_but_state_updates() -> None:
    tracker = HealthStateTracker()
    tracker.set_initial("container-id", "healthy")

    observation = record_health_observation(
        tracker,
        container_id="container-id",
        health="starting",
        send_starting=False,
    )

    assert observation is not None
    assert observation.alert_status is None
    assert tracker.current_health("container-id") == "starting"

    tracker.set_initial("second-container-id", "healthy")
    starting_observation = record_health_observation(
        tracker,
        container_id="second-container-id",
        health="starting",
        send_starting=True,
    )

    assert starting_observation is not None
    assert starting_observation.alert_status == "starting"


def test_state_is_keyed_by_full_container_id_not_name() -> None:
    tracker = HealthStateTracker()

    tracker.set_initial("full-id-1", "healthy")
    tracker.set_initial("full-id-2", "unhealthy")

    assert tracker.current_health("full-id-1") == "healthy"
    assert tracker.current_health("full-id-2") == "unhealthy"


def test_remove_deletes_container_state() -> None:
    tracker = HealthStateTracker()
    tracker.set_initial("container-id", "healthy")

    tracker.remove("container-id")

    assert tracker.current_health("container-id") is None
