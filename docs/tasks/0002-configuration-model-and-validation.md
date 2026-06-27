Task 0002: Configuration Model And Validation
=============================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement YAML configuration loading, defaults, validation, and route reference
checks.

Related Docs
------------

- `docs/configuration.md`
- `docs/requirements.md`
- `docs/security.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Load configuration from `CONFIG_FILE` or the default config path.
- Implement monitor defaults.
- Validate monitor mode.
- Validate receiver names and plugin references.
- Validate route receiver references.
- Parse duration values.
- Define secret file validation behavior for receiver initialization.

Out Of Scope
------------

- Docker connection logic.
- Plugin delivery implementation.
- Runtime event loop.

Dependencies
------------

- 0001

Implementation Notes
--------------------

Validation errors should identify the failing field and be safe to log. Unknown
configured plugins should fail startup clearly without importing unused plugins.

Task-Specific Acceptance Criteria
---------------------------------

- YAML config loads from file.
- Defaults match `docs/configuration.md`.
- Invalid monitor modes fail validation.
- Duplicate receiver names fail validation.
- Route references to unknown receivers fail validation.
- Unknown plugin names fail validation.
- Duration parsing is covered by tests.
- Config docs are updated with final behavior.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0001.

Implemented artifacts:

- `docker_health_alerts/config.py` with YAML loading, defaults, pydantic models,
  duration parsing, receiver validation, route validation, known plugin
  validation, and secret file reference validation.
- `docker_health_alerts/cli.py` `config-check` command.
- `tests/test_config.py` for defaults, invalid monitor modes, duplicate
  receivers, route references, plugin names, duration parsing, environment
  config path loading, and secret file validation.
- `tests/e2e/test_cli_config_check.py` for end-to-end config validation through
  the CLI.
- Runtime dependencies `pydantic` and `PyYAML`, plus `types-PyYAML`, installed
  and locked through `uv`.

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

- `uv sync` installed and locked the new config dependencies.
- Unit/component test gate passed: 23 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.

Document sweep:

- Updated `README.md`, `docs/configuration.md`, and `docs/operations.md` with
  the `uv run docker-health-alerts config-check --config ...` command.
- Checked `docs/requirements.md`, `docs/architecture.md`, `docs/security.md`,
  `docs/testing.md`, and `docs/plugin_contract.md`; no behavior changes were
  needed beyond the config validation command.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Configuration parsing is isolated in `docker_health_alerts/config.py`.
- Plugin-name validation uses a small provider-neutral registry constant without
  importing plugin modules.
- Secret file validation verifies readability without reading or logging secret
  contents.
- Tests use temporary files and do not require Docker daemon access or receiver
  credentials.

Residual risk:

- Plugin-specific required fields are intentionally minimal until receiver
  initialization tasks implement the concrete plugins.
