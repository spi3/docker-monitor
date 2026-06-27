Testing Strategy
================

Status: initial testing strategy

Purpose
-------

This document defines the testing approach for DockerMonitor. The
core service should be testable without a live Docker daemon, while still
allowing optional integration tests against Docker when available.

Test Layers
-----------

Use three test layers:

1. Unit tests for pure logic.
2. Component tests with fake Docker sources and fake receivers.
3. Optional integration tests against Docker and HTTP endpoints.
4. Docker-in-Docker end-to-end tests for the full container runtime.

The default test suite should not require Docker daemon access or real receiver
credentials.

Unit Test Scope
---------------

Unit tests should cover:

- Configuration parsing and validation.
- Duration parsing.
- Monitor mode behavior.
- Optional container filters.
- Label redaction.
- Healthcheck output truncation.
- Alert normalization.
- State tracking and duplicate suppression.
- Route matching.
- Plugin registry errors.
- Delivery result classification.
- Discord payload formatting.
- Generic webhook payload construction.

Configuration Tests
-------------------

Configuration tests should verify:

- Default monitor mode is `label_opt_in`.
- Default monitor label is `docker-monitor.enable`.
- `send_resolved` defaults to `true`.
- `send_starting` defaults to `false`.
- Duplicate receiver names are rejected.
- Routes referencing unknown receivers are rejected.
- Unknown plugin aliases are rejected with clear messages.
- Dotted external plugin module paths are accepted and loaded only when used.
- Invalid durations are rejected.
- Secret file config is validated during receiver initialization.

Filtering Tests
---------------

Filtering tests should include:

- `label_opt_in` monitors only label value `true`.
- `label_opt_out` excludes only label value `false`.
- Label boolean comparisons are case-insensitive.
- Missing labels are ignored in opt-in mode.
- Missing labels are monitored in opt-out mode.
- Name filters match normalized names without leading slash.
- Image filters match expected image references.
- Compose project and service filters use Docker Compose labels.
- Arbitrary label filters require configured key/value matches.

State Tests
-----------

State tests should prove duplicate suppression:

```text
unknown -> unhealthy   emits firing
unhealthy -> unhealthy suppresses
unhealthy -> healthy   emits resolved when enabled
healthy -> healthy     suppresses
healthy -> starting    emits only when send_starting is enabled
```

State must be keyed by full container ID.

Startup Reconciliation Tests
----------------------------

Startup reconciliation tests should use fake containers and verify:

- Containers without healthchecks are ignored.
- Unmonitored containers are ignored.
- Existing unhealthy monitored containers emit startup `firing` alerts.
- Existing healthy monitored containers initialize state without alerting.
- Existing starting containers alert only when `send_starting` is enabled.
- Healthcheck log output is truncated before delivery.
- Redacted labels are included in alerts.

Alert Normalization Tests
-------------------------

Alert tests should verify the normalized object contains:

- `version`
- `status`
- `alert`
- `host`
- `severity`
- `container`
- `compose`
- `labels`
- `event`
- `health_log`

Tests should verify Compose fields are populated from:

- `com.docker.compose.project`
- `com.docker.compose.service`

Plugin Tests
------------

Plugin registry tests should verify:

- Only configured plugins are imported.
- Missing configured plugins fail startup clearly.
- Multiple receiver instances can use the same plugin.
- Plugin initialization receives only plugin-specific config.
- External plugin module paths are loaded through the same receiver contract.

Generic webhook tests should verify:

- Default payload is the normalized alert object.
- Custom headers are applied.
- Header file values are loaded.
- URLs and secret headers are not logged.
- Network errors are retryable.
- Non-2xx responses are retryable.
- 2xx responses are successful.

Discord tests should verify:

- `firing` payloads identify unhealthy containers.
- `resolved` payloads identify recovered containers.
- `starting` payloads are supported when emitted by core.
- Webhook URLs are loaded from files.
- Webhook URLs are redacted from logs and error messages.
- Discord 5xx responses are retryable.
- Discord 2xx responses are successful.

Routing Tests
-------------

Routing tests should verify:

- Exact severity match.
- Exact status match.
- Nested container field match.
- Nested Compose field match.
- Multiple receivers per route.
- No-match behavior logs and drops without error.
- Unknown route receiver names are rejected during configuration validation.

Retry Tests
-----------

Retry tests should verify:

- `success` stops retrying.
- `permanent_failure` is not retried.
- `retryable_failure` is retried up to configured attempts.
- Attempt numbers are logged.
- A failing receiver does not prevent other receivers from running.
- Fatal receiver behavior stops the service only when configured.

Integration Tests
-----------------

Optional Docker integration tests may verify:

- Docker client connects through the default socket.
- Container inspection reads health state.
- Docker event subscription receives `health_status` events.
- Reconnect logic resumes after stream interruption.

These tests should be opt-in because they require Docker daemon access.

Suggested marker:

```sh
uv run pytest -m docker
```

Full Docker-in-Docker end-to-end validation starts a privileged `docker:dind`
container, loads the DockerMonitor runtime image into the nested daemon, starts
DockerMonitor inside that daemon, and runs monitored test containers with real
Docker healthchecks.

The DinD test mounts a test-only receiver plugin into the DockerMonitor
container. The plugin drops delivery and emits JSON log records with
`event=mock_receiver.alert_received`. The test drives an unhealthy startup
container plus a flapping container and asserts that `firing` and `resolved`
alerts are logged.

Run the privileged DinD e2e locally with:

```sh
DOCKER_MONITOR_RUN_DIND_E2E=1 uv run pytest -m "e2e and docker"
```

CI enables `DOCKER_MONITOR_RUN_DIND_E2E=1` for the end-to-end test step. The
general unit/component step runs `uv run pytest -m "not docker"` so it does not
launch privileged containers.

Containerized validation for the end-to-end CLI checks uses the Dockerfile test
target:

```sh
docker build --target test -t docker-monitor:test .
docker run --rm docker-monitor:test
```

GitHub Actions runs the same local gates plus container build and containerized
end-to-end validation. See `docs/release.md`.

Secret Redaction Tests
----------------------

Redaction tests should inspect log output and delivery result messages to ensure
they do not contain:

- Webhook URLs.
- Authorization header values.
- File-loaded secret values.
- Token-like label values.

Tests should include mixed-case sensitive label names such as:

- `ApiToken`
- `SECRET_KEY`
- `authorization`

Test Fixtures
-------------

Recommended fixtures:

- Fake Docker container metadata objects.
- Fake Docker event stream.
- Fake receiver plugin returning controlled delivery results.
- Temporary secret files.
- Captured JSON log records.
- Example normalized alerts.

No-Live-Docker Requirement
--------------------------

The core engine should be designed so the main test suite can run without
Docker. Docker SDK calls should be isolated behind a source adapter that can be
replaced by test fakes.

This keeps CI fast, deterministic, and usable on systems without Docker socket
access.
