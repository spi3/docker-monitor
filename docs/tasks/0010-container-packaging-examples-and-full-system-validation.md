Task 0010: Container Packaging, Examples, And Full System Validation
====================================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Finalize container packaging, deployment examples, and full system validation
for the initial implementation.

Related Docs
------------

- `docs/operations.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/tech_stack.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Build final container image.
- Confirm runtime dependencies are minimal.
- Validate Docker run example.
- Validate Docker Compose example.
- Validate config and secret mount behavior.
- Run full unit, component, and end-to-end test suites.
- Run build, lint, formatting, and type-check commands.
- Perform final documentation and maintainability sweeps.

Out Of Scope
------------

- New feature development beyond release-hardening fixes.
- Additional receiver providers.
- UI or remediation behavior.

Dependencies
------------

- 0009

Implementation Notes
--------------------

This task proves the service works as a containerized application and that docs
match the implemented runtime behavior.

Task-Specific Acceptance Criteria
---------------------------------

- Container image builds successfully.
- Container starts with documented config and socket mounts.
- Healthcheck works in the container.
- Full end-to-end test suite passes.
- Documentation examples match tested commands.
- Security guidance matches final implementation.
- Release readiness evidence is recorded.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0009.

Implemented artifacts:

- Multi-stage `Dockerfile` with `base`, `test`, and `runtime` targets.
- Runtime image installs only non-dev dependencies with `uv sync --locked
  --no-dev --no-cache`.
- Test image installs dev dependencies and runs the end-to-end test marker.
- Runtime image runs as non-root `appuser`.
- Runtime default command is `run --config /config/config.yaml`.
- `examples/config.yaml`, `examples/compose.yaml`, `examples/secrets/`, and
  `examples/README.md`.
- Documentation updates in `docs/operations.md`, `docs/testing.md`,
  `docs/tech_stack.md`, and `docs/security.md`.

Commands run:

```sh
uv --cache-dir .uv-cache run pytest
uv --cache-dir .uv-cache run pytest -m e2e
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run ruff format --check .
uv --cache-dir .uv-cache run mypy .
uv --cache-dir .uv-cache build
docker compose -f examples/compose.yaml config
docker build --target runtime -t docker-monitor:local .
docker build --target test -t docker-monitor:test .
docker run --rm docker-monitor:local healthcheck
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /home/spi/repos/docker-monitor/examples/config.yaml:/config/config.yaml:ro \
  -v /home/spi/repos/docker-monitor/examples/secrets:/run/secrets:ro \
  docker-monitor:local config-check --config /config/config.yaml
docker run --rm docker-monitor:test
docker run --rm --entrypoint /app/.venv/bin/python \
  docker-monitor:local \
  -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') is None else 1)"
docker run --rm --entrypoint id docker-monitor:local -u
```

Results:

- Unit/component test gate passed: 100 tests passed.
- End-to-end gate passed locally: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.
- Compose config validation passed.
- Runtime image built successfully.
- Test image built successfully.
- Runtime container healthcheck returned `{"status": "ok"}`.
- Runtime container config-check with documented socket, config, and secret
  mounts returned `{"status": "ok", "receivers": 1, "routes": 1}`.
- Containerized end-to-end test suite passed: 2 selected tests passed.
- Runtime image does not include `pytest`.
- Runtime container effective user ID is `1000`.

Document sweep:

- Updated `docs/operations.md` with container validation commands and examples.
- Updated `docs/testing.md` with Dockerfile test-target validation commands.
- Updated `docs/tech_stack.md` to document the Dockerfile test target.
- Updated `docs/security.md` to clarify example secret values.
- Checked `docs/requirements.md`, `docs/architecture.md`,
  `docs/configuration.md`, and `docs/plugin_contract.md`; no additional
  changes were required.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Dockerfile separates runtime and test dependency surfaces.
- Runtime image uses the locked dependency graph and excludes dev dependencies.
- Examples are under `examples/` and do not alter production code paths.
- Containerized tests use the existing `pytest -m e2e` marker.

Residual risk:

- Publishing, CI, and release/version automation are handled by Task 0011.
