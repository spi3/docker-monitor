Task 0006: Routing, Delivery Coordination, And Retries
======================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement alert routing, receiver dispatch, structured delivery results, retry
handling, and failure isolation.

Related Docs
------------

- `docs/architecture.md`
- `docs/plugin_contract.md`
- `docs/configuration.md`
- `docs/testing.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Match routes against normalized alert fields.
- Dispatch alerts to named receivers.
- Define delivery result statuses.
- Retry retryable failures.
- Avoid retrying permanent failures.
- Continue delivery to other receivers after one receiver fails.
- Log delivery attempts as structured JSON.

Out Of Scope
------------

- Provider-specific payload formatting.
- Docker event consumption.
- Final runtime signal handling.

Dependencies
------------

- 0002
- 0003

Implementation Notes
--------------------

Routing should depend only on normalized alert data. The delivery coordinator
should not know provider-specific request formats.

Task-Specific Acceptance Criteria
---------------------------------

- Exact route matching works for top-level and nested alert fields.
- Multiple receivers per route are supported.
- Unmatched alerts are logged and dropped without error.
- Retry behavior follows delivery result status.
- Attempt counts are bounded and logged.
- Fatal receiver behavior is implemented or explicitly scoped for a later task.
- Delivery logs do not contain secrets.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0005.

Implemented artifacts:

- `docker_health_alerts/plugins.py` with provider-neutral `DeliveryResult`,
  delivery statuses, and receiver protocol.
- `docker_health_alerts/routing.py` with exact top-level and nested alert field
  route matching, receiver de-duplication, and unmatched-route structured logs.
- `docker_health_alerts/delivery.py` with receiver dispatch, bounded retries,
  permanent failure handling, exception classification, fatal receiver behavior,
  and structured secret-safe delivery logs.
- `tests/test_routing.py` covering exact severity/status-style matching, nested
  container and Compose fields, multiple receivers, de-duplication, and
  unmatched-route logging.
- `tests/test_delivery.py` covering retryable failures, permanent failures,
  receiver exceptions, failure isolation, fatal behavior, and secret-safe logs.

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

- Unit/component test gate passed: 74 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.

Document sweep:

- Checked `docs/architecture.md`, `docs/plugin_contract.md`,
  `docs/configuration.md`, `docs/testing.md`, and `docs/requirements.md`;
  implemented route and delivery behavior matches the documented contract.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Routing depends only on normalized alert data.
- Delivery coordination depends only on the receiver protocol and delivery
  result contract.
- Provider-specific payload formatting was not introduced.
- Delivery logs omit alert payloads and delivery messages to avoid leaking
  secrets.

Residual risk:

- Concrete receiver plugin loading and provider delivery are implemented in
  Tasks 0007 and 0008.
