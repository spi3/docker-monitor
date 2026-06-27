Task 0009: Runtime Loop, Reconnects, Shutdown, And Healthcheck
==============================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement the main service runtime loop, reconnect behavior, graceful shutdown,
and healthcheck command or endpoint.

Related Docs
------------

- `docs/architecture.md`
- `docs/operations.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Run startup reconciliation before live event consumption.
- Consume Docker health events continuously.
- Reconnect after Docker stream disconnects.
- Reconcile after reconnect.
- Handle `SIGTERM` and `SIGINT`.
- Give in-flight deliveries a bounded grace period.
- Provide healthcheck command or endpoint.
- Emit structured JSON logs to stdout.

Out Of Scope
------------

- New receiver plugins.
- New monitor filter types.
- UI or metrics endpoint.

Dependencies
------------

- 0005
- 0006
- 0007
- 0008

Implementation Notes
--------------------

The event loop should isolate receiver failures from Docker event consumption
unless fatal behavior is configured.

Task-Specific Acceptance Criteria
---------------------------------

- Startup sequence matches `docs/architecture.md`.
- Reconnect behavior uses bounded backoff.
- Reconciliation runs after reconnect.
- Shutdown path stops new event consumption.
- In-flight delivery grace period is tested.
- Healthcheck behavior is documented and tested.
- JSON logs include stable operational fields.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0008.

Implemented artifacts:

- `docker_monitor/structured_logging.py` JSON logger for stdout records.
- `docker_monitor/runtime.py` service runtime with startup
  reconciliation, alert routing/delivery, live Docker health event processing,
  reconnect after stream disconnects, reconciliation after reconnect, shutdown
  request handling, and signal handler installation.
- `docker_monitor/cli.py` `run --config` integration using the runtime.
- Existing `healthcheck` command retained and tested.
- `tests/test_runtime.py` covering startup reconciliation before streaming,
  live event alert delivery, stream reconnects, reconnect-limit failure,
  shutdown grace-period logging, and structured JSON log output.
- Updated CLI tests for runtime startup-failure behavior.

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

- Unit/component test gate passed: 100 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.

Document sweep:

- Updated `README.md` and `docs/operations.md` with `run --config`, reconnect,
  structured logging, and shutdown behavior.
- Checked `docs/architecture.md`, `docs/requirements.md`, `docs/security.md`,
  and `docs/testing.md`; implemented behavior matches the documented runtime
  requirements.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Runtime orchestration is isolated from Docker SDK details, receiver plugin
  formatting, and route matching internals.
- Tests use fake sources and fake receivers; no Docker daemon or real receiver
  credentials are required.
- Runtime logs avoid alert payloads and secret values.
- Signal handling is isolated to the runtime entry path.

Residual risk:

- Full containerized validation is handled by Task 0010.
