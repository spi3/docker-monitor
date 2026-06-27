Docker Health Alert Monitor Tech Stack
=====================================

Status: proposed initial stack

Runtime
-------

Use Python 3.12 or newer for the initial service.

Python is a good fit for this project because the service is IO-bound, the
Docker SDK is mature, packaging is straightforward, and receiver plugins can be
implemented with a small interface without bringing in a large framework.

Core Dependencies
-----------------

The core service should keep dependencies intentionally small:

- `docker`: Docker Engine API client for startup inspection and event stream
  consumption.
- `PyYAML`: File-based YAML configuration parsing.
- `httpx`: HTTP client used by HTTP-based receiver plugins.
- `pydantic`: Configuration and alert model validation.

The core event engine should not depend on provider-specific SDKs. Integrations
such as Discord, Slack, ntfy, Gotify, SMTP, or Pushover must live behind the
receiver plugin interface.

Plugin Loading
--------------

Initial plugins can live in a local package namespace, for example:

```text
docker_health_alerts.receivers.generic_webhook
docker_health_alerts.receivers.discord
```

The plugin registry should map configured plugin names to import paths. A plugin
module should only be imported when a receiver references that plugin in the
configuration file.

Initial plugin names:

- `generic-webhook`
- `discord`

Future plugin discovery can move to Python entry points if this project becomes
distributed as an installable package with third-party plugins.

Configuration
-------------

Use YAML as the primary configuration format.

Recommended default config path inside the container:

```text
/config/config.yaml
```

The service may support an environment variable such as `CONFIG_FILE` to point
to a different config file. Provider secrets should prefer file references such
as `webhook_url_file` over inline secret values.

Logging
-------

Use standard library logging with a JSON formatter.

Logs must be written to stdout and should include stable fields such as:

- `level`
- `time`
- `event`
- `container_id`
- `container_name`
- `alert_status`
- `receiver`
- `delivery_status`
- `attempt`

Logs must not include webhook URLs, tokens, auth headers, or secret file
contents.

HTTP Delivery
-------------

Use `httpx` for receiver HTTP calls.

Recommended behavior:

- Use explicit request timeouts.
- Treat network exceptions as retryable.
- Treat non-2xx HTTP responses as retryable unless a plugin documents a more
  specific permanent failure condition.
- Redact URLs and sensitive headers from logs.

Container Image
---------------

Build a small Python runtime image.

Recommended base image:

```text
python:3.12-slim
```

The image should:

- Install only runtime dependencies.
- Run as a non-root user when possible.
- Read configuration from `/config/config.yaml` by default.
- Expose no public port unless an HTTP health endpoint is implemented.
- Include a healthcheck command.

Docker Runtime
--------------

The container needs access to the Docker Engine API.

Typical Docker socket mount:

```text
/var/run/docker.sock:/var/run/docker.sock:ro
```

Docker socket access is privileged even when mounted read-only. Anyone who can
use the Docker socket can often inspect sensitive container metadata and may be
able to affect the host depending on daemon configuration.

Testing
-------

Use `pytest` for unit tests.

Initial test coverage should include:

- Configuration validation.
- Monitor label filtering.
- Optional name, image, Compose, and arbitrary label filters.
- Health state duplicate suppression.
- Startup reconciliation behavior.
- Alert normalization and health log truncation.
- Label redaction.
- Route matching.
- Plugin registry error handling.
- Generic webhook retry classification.
- Discord payload formatting without leaking webhook URLs.

Code Quality
------------

Use:

- `uv` for virtual environment management and command execution.
- `ruff` for linting and import sorting.
- `mypy` or pyright-compatible type hints where practical.
- `pytest` for test execution.

The implementation should keep the core event engine testable without a live
Docker daemon by isolating Docker API calls behind a small source adapter.

Project Layout
--------------

Recommended initial layout:

```text
docker_health_alerts/
  __init__.py
  __main__.py
  alerts.py
  config.py
  docker_source.py
  engine.py
  filters.py
  logging.py
  plugins.py
  routing.py
  state.py
  receivers/
    __init__.py
    discord.py
    generic_webhook.py
tests/
  test_alerts.py
  test_config.py
  test_filters.py
  test_plugins.py
  test_routing.py
  test_state.py
```

Dependency Boundary
-------------------

The core package may define:

- Alert schemas.
- Receiver plugin interface.
- Delivery result schemas.
- Docker source adapter interface.
- Routing and retry orchestration.

Receiver plugins may define:

- Provider-specific payload formatting.
- Provider-specific config parsing.
- Provider-specific delivery behavior.

Receiver plugins must not define Docker event handling, monitor filtering,
startup reconciliation, or core state transitions.
