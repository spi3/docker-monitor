Task 0004: Monitor Filtering And Health State Tracking
======================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement monitor filtering, health state tracking by container ID, and
duplicate suppression.

Related Docs
------------

- `docs/configuration.md`
- `docs/requirements.md`
- `docs/architecture.md`
- `docs/testing.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Implement `label_opt_in`.
- Implement `label_opt_out`.
- Implement optional filters for name, image, Compose project, Compose service,
  and arbitrary labels.
- Track health state by full container ID.
- Suppress unchanged health states.
- Preserve state updates even when an alert type is disabled.

Out Of Scope
------------

- Docker event stream consumption.
- Receiver delivery.
- Startup reconciliation against real Docker.

Dependencies
------------

- 0002
- 0003

Implementation Notes
--------------------

Filtering should be deterministic and easy to test with simple container
metadata fixtures. State tracking should not depend on container names.

Task-Specific Acceptance Criteria
---------------------------------

- Label monitor modes match documented behavior.
- Optional filters combine predictably after monitor mode filtering.
- Duplicate unchanged health states are suppressed.
- State is keyed by full container ID.
- `send_resolved` and `send_starting` settings do not prevent state updates.
- Unit tests cover transition edge cases.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0003.

Implemented artifacts:

- `docker_health_alerts/filters.py` with `label_opt_in`, `label_opt_out`,
  optional name, image, Compose project, Compose service, and arbitrary label
  filtering.
- `docker_health_alerts/state.py` with full-container-ID health state tracking,
  duplicate suppression, and alert-status observation helpers.
- `tests/test_filters.py` covering label modes, case-insensitive label booleans,
  normalized names, image references, Compose labels, arbitrary labels, and
  digest/tag image matching.
- `tests/test_state.py` covering unknown-to-unhealthy, duplicate suppression,
  resolved transitions, disabled resolved/starting state updates, full-ID
  state keys, and state removal.

Commands run:

```sh
uv --cache-dir .uv-cache run pytest
uv --cache-dir .uv-cache run pytest -m e2e
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run ruff format --check .
uv --cache-dir .uv-cache run mypy .
uv --cache-dir .uv-cache build
```

Results:

- Unit/component test gate passed: 53 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.

Document sweep:

- Checked `docs/configuration.md`, `docs/requirements.md`,
  `docs/architecture.md`, and `docs/testing.md`; implemented behavior matches
  the documented filtering and state requirements.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Filtering is isolated from Docker API access.
- State tracking is independent of container names and keyed by full container
  ID.
- Disabled alert settings still update state through a single tested helper.
- No provider-specific code was introduced.

Residual risk:

- Docker event data conversion into `ContainerSnapshot` is implemented in Task
  0005.
