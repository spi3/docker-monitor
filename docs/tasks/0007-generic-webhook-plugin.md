Task 0007: Generic Webhook Plugin
=================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement the optional `generic-webhook` receiver plugin.

Related Docs
------------

- `docs/plugin_contract.md`
- `docs/configuration.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Load plugin only when configured.
- Support `url` and `url_file`.
- Support custom headers.
- Support header values loaded from files.
- Send normalized alert object as JSON by default.
- Classify HTTP and network delivery results.
- Redact URLs and secret headers from logs.

Out Of Scope
------------

- Discord formatting.
- Docker event handling.
- Third-party webhook provider-specific transforms.

Dependencies
------------

- 0006

Implementation Notes
--------------------

The plugin should use the shared delivery result contract. Secret values loaded
from files must not appear in exceptions, logs, or test snapshots.

Task-Specific Acceptance Criteria
---------------------------------

- Plugin is imported only when referenced by configuration.
- URL file loading strips one trailing newline.
- Static and file-loaded headers are applied.
- Default request body is the normalized alert object.
- 2xx responses return success.
- Network errors and non-2xx responses are retryable by default.
- Secret redaction tests cover URLs and header values.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0006.

Implemented artifacts:

- `docker_monitor/secrets.py` with shared secret-file reading that strips
  one trailing newline.
- `docker_monitor/plugins.py` plugin registry and receiver loading.
- `docker_monitor/receivers/generic_webhook.py` with `httpx` POST
  delivery, `url`/`url_file`, `WEBHOOK_URL`/`WEBHOOK_URL_FILE`, static headers,
  `header_files`, default normalized-alert JSON payloads, JSON
  `payload_template` rendering, and retry classification.
- `tests/test_plugins.py` covering configured-only plugin import behavior,
  one-import-per-plugin behavior, and missing plugin startup errors.
- `tests/test_generic_webhook.py` covering URL-file newline stripping, headers,
  header files, default payloads, template payloads, 2xx success, network
  retryable failures, non-2xx retryable failures, and secret-safe result
  messages.

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

- Unit/component test gate passed: 86 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.

Document sweep:

- Updated `docs/configuration.md` and `docs/plugin_contract.md` with the
  implemented `payload_template` token behavior.
- Checked `docs/security.md`, `docs/testing.md`, and `docs/requirements.md`;
  implemented behavior matches the documented requirements.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Receiver loading is centralized in `docker_monitor/plugins.py`.
- Secret file reading is shared through `docker_monitor/secrets.py`.
- The generic webhook plugin does not import or inspect Docker SDK objects.
- Delivery results and error messages avoid webhook URLs and secret header
  values.

Residual risk:

- Discord remains intentionally missing until Task 0008.
