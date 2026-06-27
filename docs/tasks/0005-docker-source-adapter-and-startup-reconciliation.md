Task 0005: Docker Source Adapter And Startup Reconciliation
===========================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement Docker API access, container inspection, startup reconciliation, and
health event subscription behind a testable source adapter.

Related Docs
------------

- `docs/architecture.md`
- `docs/requirements.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Connect to Docker through `/var/run/docker.sock` or `DOCKER_HOST`.
- Inspect existing containers.
- Ignore containers without healthchecks.
- Reconcile current health state at startup.
- Emit startup firing alerts for already unhealthy monitored containers.
- Subscribe to `type=container` and `event=health_status` events.
- Provide fakes for tests without live Docker.

Out Of Scope
------------

- Receiver plugin implementation.
- Final reconnect loop.
- Container image packaging.

Dependencies
------------

- 0003
- 0004

Implementation Notes
--------------------

The Docker SDK should be isolated so core reconciliation can be tested with fake
container metadata and fake events.

Task-Specific Acceptance Criteria
---------------------------------

- Docker adapter has a narrow interface.
- Startup reconciliation follows documented order.
- Containers without healthchecks are ignored.
- Already unhealthy monitored containers emit startup firing alerts.
- Healthy containers initialize without alerting.
- Starting containers alert only when enabled.
- Event subscription filters are correct.
- Tests do not require Docker by default.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0004.

Implemented artifacts:

- Runtime dependency `docker` installed and locked through `uv`.
- `docker_monitor/docker_source.py` with a narrow Docker SDK adapter,
  container inspection snapshots, healthcheck detection, health log extraction,
  Docker event filters, and health event parsing.
- `docker_monitor/reconciliation.py` with startup reconciliation over a
  source protocol.
- `ContainerSnapshot.has_healthcheck` field for core filtering of containers
  without Docker healthchecks.
- `tests/test_docker_source.py` covering Docker metadata parsing, healthcheck
  detection, event parsing, event filters, and `docker.from_env` source setup.
- `tests/test_reconciliation.py` covering startup firing alerts, healthy
  initialization without alerts, optional starting alerts, unmonitored
  containers, and containers without healthchecks.

Commands run:

```sh
uv --cache-dir .uv-cache sync --python 3.12
uv --cache-dir .uv-cache run pytest
uv --cache-dir .uv-cache run pytest -m e2e
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run ruff format --check .
uv --cache-dir .uv-cache run mypy .
uv --cache-dir .uv-cache build
```

Results:

- `uv sync` installed and locked the Docker SDK.
- Unit/component test gate passed: 64 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.
- The first sandboxed build attempt failed due blocked network access for the
  isolated build backend; rerunning the same `uv build` with approved network
  access passed.

Document sweep:

- Checked `docs/architecture.md`, `docs/requirements.md`, `docs/security.md`,
  `docs/testing.md`, `docs/operations.md`, and `docs/tech_stack.md`; the Docker
  source and reconciliation behavior matches the documented requirements.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Docker SDK objects are isolated in `docker_monitor/docker_source.py`.
- Startup reconciliation depends on a source protocol and is tested with fakes.
- Provider-specific delivery code was not introduced.
- The default test suite does not require Docker daemon access.

Residual risk:

- Live Docker integration tests remain optional and are not required by the
  default suite.
