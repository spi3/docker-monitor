Task 0003: Alert Model, Redaction, And Normalization
====================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement the provider-neutral alert model, label redaction, healthcheck output
truncation, and Docker-to-alert normalization helpers.

Related Docs
------------

- `docs/requirements.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/plugin_contract.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Define alert schema version `1`.
- Populate container identity and health fields.
- Populate Compose project and service fields.
- Redact sensitive labels.
- Truncate healthcheck output.
- Map Docker health states to alert statuses.
- Keep raw Docker objects outside plugin inputs.

Out Of Scope
------------

- Docker API calls.
- Receiver formatting.
- Routing and retries.

Dependencies
------------

- 0001
- 0002

Implementation Notes
--------------------

The normalized alert object is the boundary between core and receiver plugins.
Keep this model stable and explicit.

Task-Specific Acceptance Criteria
---------------------------------

- Alert schema includes all required top-level fields.
- Sensitive labels are redacted case-insensitively.
- Health log output respects configured length.
- Compose labels are mapped correctly.
- Alert status mapping is tested.
- Plugins receive normalized alert dictionaries or models only.
- Documentation examples remain accurate.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0002.

Implemented artifacts:

- `docker_monitor/alerts.py` with normalized alert schema version `1`.
- `ContainerSnapshot` and `HealthLogSnapshot` inputs that keep Docker SDK
  objects outside the provider-facing alert boundary.
- Alert status mapping for `unhealthy`, `healthy`, and `starting`.
- Case-insensitive label redaction using the documented sensitive label tokens.
- Healthcheck output truncation.
- Compose project/service extraction from Docker Compose labels.
- `tests/test_alerts.py` covering schema shape, redaction, truncation, status
  mapping, event time formatting, and container name normalization.

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

- Unit/component test gate passed: 34 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.

Document sweep:

- Checked `docs/requirements.md`, `docs/architecture.md`,
  `docs/plugin_contract.md`, `docs/security.md`, `docs/testing.md`, and
  `docs/configuration.md`; the implemented schema matches the documented alert
  example and no schema doc changes were required.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Alert normalization is isolated in `docker_monitor/alerts.py`.
- Provider-facing output is a pydantic model/dictionary, not Docker SDK data.
- Redaction and truncation helpers are small, deterministic, and directly
  tested.
- No provider-specific formatting was introduced.

Residual risk:

- Docker source conversion into `ContainerSnapshot` is implemented in Task 0005.
