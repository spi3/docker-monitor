DockerMonitor Requirements
=======================================

Status: initial implementation requirements

Purpose
-------

Build a small containerized service that watches Docker container health
transitions and sends alerts through modular receiver plugins. Provider-specific
integrations must live outside the core event engine and must only be loaded
when referenced in configuration.

Core Responsibilities
---------------------

The core service must:

- Connect to Docker through `/var/run/docker.sock` or `DOCKER_HOST`.
- Subscribe to Docker events with:
  - `type=container`
  - `event=health_status`
- Reconcile current container health state on startup.
- Ignore containers that do not define a Docker healthcheck.
- Filter which containers are monitored.
- Normalize Docker health transitions into an internal alert object.
- Track previous health state by container ID.
- Suppress duplicate alerts for unchanged state.
- Route normalized alerts to configured receiver plugins.
- Handle retries, structured logging, reconnects, and graceful shutdown.

The core service must not contain Discord-specific, Slack-specific, ntfy-specific,
or other provider-specific alert formatting logic.

Alert Statuses
--------------

The service must support these normalized alert statuses:

- `firing`: A monitored container becomes unhealthy.
- `resolved`: A previously unhealthy monitored container becomes healthy.
- `starting`: A monitored container reports starting health state.

`starting` alerts must be disabled by default.

Duplicate Suppression
---------------------

The service must maintain health state by Docker container ID. If an observed
transition does not change the previously recorded health state for that
container ID, no alert should be emitted.

Startup Reconciliation
----------------------

On startup, before consuming live events, the service must:

- Inspect existing containers.
- Ignore containers without healthchecks.
- Apply the configured monitor filters.
- Initialize state for monitored containers.
- Emit a startup `firing` alert for each monitored container that is already
  unhealthy.
- Initialize healthy containers without alerting unless explicitly configured
  otherwise.
- Respect the `send_starting` setting for containers currently in `starting`
  health state.

After reconciliation completes, the service must begin consuming live Docker
health events.

Filtering
---------

Filtering must be GitOps-friendly and label-first.

Default settings:

```yaml
monitor:
  mode: label_opt_in
  label: docker-monitor.enable
```

Mode behavior:

- `label_opt_in`: Monitor only containers where the configured monitor label is
  set to `true`.
- `label_opt_out`: Monitor all containers except containers where the configured
  monitor label is set to `false`.

The service should also support optional filters for:

- Container name.
- Image name.
- Docker Compose project label:
  `com.docker.compose.project`.
- Docker Compose service label:
  `com.docker.compose.service`.
- Arbitrary labels.

Internal Alert Model
--------------------

The core service must convert Docker health transitions into a provider-neutral
alert object.

Example:

```json
{
  "version": "1",
  "status": "firing",
  "alert": "DockerContainerUnhealthy",
  "host": "serenity",
  "severity": "warning",
  "container": {
    "id": "abc123",
    "name": "qbittorrent",
    "image": "lscr.io/linuxserver/qbittorrent:latest",
    "state": "running",
    "health": "unhealthy",
    "previous_health": "healthy"
  },
  "compose": {
    "project": "gt",
    "service": "qbittorrent"
  },
  "labels": {},
  "event": {
    "source": "docker",
    "time": "2026-06-27T17:00:00Z"
  },
  "health_log": {
    "exit_code": 1,
    "output": "truncated healthcheck output"
  }
}
```

Required top-level fields:

- `version`: Alert schema version. Initial value is `"1"`.
- `status`: One of `firing`, `resolved`, or `starting`.
- `alert`: Stable alert name. Initial value is `DockerContainerUnhealthy`.
- `host`: Hostname from configuration or runtime hostname detection.
- `severity`: Alert severity. Default is `warning`.
- `container`: Container identity and health details.
- `compose`: Compose project and service values when present.
- `labels`: Redacted labels safe to expose to receivers.
- `event`: Event source and timestamp.
- `health_log`: Most recent Docker healthcheck log entry when available.

Healthcheck log output must be truncated according to configuration.

Plugin System
-------------

Alert receivers must be implemented as plugins.

Plugin requirements:

- Plugins are loaded only when referenced in configuration.
- Unused plugins and their dependencies are not initialized.
- A configured plugin that cannot be found must fail startup with a clear error.
- Plugin failures must not crash the core event loop unless that receiver or
  route is configured as fatal.
- Plugins receive the normalized alert object and plugin-specific config.
- Plugins return a structured delivery result.

Delivery result statuses:

- `success`: Delivery completed successfully.
- `retryable_failure`: Delivery failed but may succeed if retried.
- `permanent_failure`: Delivery failed and should not be retried.

Receiver Configuration
----------------------

Configuration should be file based once plugins exist. Environment variables may
be supported for bootstrap paths, but provider settings should live in config
files or secret files.

Example:

```yaml
host: serenity

monitor:
  mode: label_opt_in
  label: docker-monitor.enable
  send_resolved: true
  send_starting: false
  health_log_output_limit: 1000

receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: /run/secrets/discord_webhook

  - name: raw-webhook
    plugin: generic-webhook
    config:
      url: https://example.internal/docker-alerts
      timeout: 10s
      retries: 3

routes:
  - match:
      severity: warning
    receivers:
      - discord-lab
```

Configuration Requirements
--------------------------

The service must validate configuration at startup.

Required validation:

- Each receiver has a unique `name`.
- Each receiver references a known `plugin`.
- Each route references existing receiver names.
- Monitor mode is one of `label_opt_in` or `label_opt_out`.
- Duration values such as `timeout` are valid.
- Secret file paths are readable when the receiver is initialized.

Generic Webhook Plugin
----------------------

The `generic-webhook` plugin must:

- Send HTTP POST requests.
- Support `url` and `url_file`.
- Support compatibility aliases `WEBHOOK_URL` and `WEBHOOK_URL_FILE` where
  environment-style configuration is used.
- Support custom headers.
- Support header values loaded from files.
- Send the normalized alert object as JSON by default.
- Optionally support a JSON payload template.
- Retry on network errors.
- Retry on non-2xx HTTP responses.
- Avoid logging secret URL, auth header, or secret header values.

Discord Plugin
--------------

The `discord` plugin must:

- Accept `webhook_url` or `webhook_url_file`.
- Support compatibility aliases `WEBHOOK_URL` and `WEBHOOK_URL_FILE` where
  environment-style configuration is used.
- Convert normalized alert objects into Discord-friendly webhook messages.
- Send messages for `firing` and `resolved` alerts.
- Respect `send_starting` behavior from the core service.
- Avoid leaking webhook URLs in logs.
- Be optional and loaded only when configured.

Routing
-------

Routes match normalized alert fields and deliver matching alerts to named
receivers.

Initial routing requirements:

- Match by exact field values.
- Support matching `severity`.
- Support multiple receivers per route.
- If no route matches, the service should log that no receivers matched and drop
  the alert without error.

Retries and Failure Handling
----------------------------

The delivery coordinator must:

- Retry `retryable_failure` results according to receiver or plugin config.
- Not retry `permanent_failure` results.
- Log structured delivery attempts and final delivery outcome.
- Continue processing Docker events when one receiver fails, unless configured
  as fatal.
- Avoid logging secret values in failure messages.

Runtime Requirements
--------------------

The service must:

- Run as a container.
- Support mounting the Docker socket read-only:

  ```text
  /var/run/docker.sock:/var/run/docker.sock:ro
  ```

- Provide a healthcheck endpoint or healthcheck command.
- Log structured JSON to stdout.
- Reconnect to the Docker event stream after disconnects.
- Support graceful shutdown on `SIGTERM` and `SIGINT`.

Security Requirements
---------------------

The service must:

- Prefer `*_file` secret inputs over inline secret values.
- Never log webhook URLs, auth headers, tokens, or secret file contents.
- Truncate healthcheck output.
- Redact sensitive labels by default.
- Document that Docker socket access is privileged even when mounted read-only.

Sensitive label names should be treated case-insensitively and should include at
least:

- `password`
- `passwd`
- `secret`
- `token`
- `key`
- `credential`
- `authorization`
- `auth`

Observability
-------------

Logs must be structured JSON and should include:

- Event type.
- Container ID and name when available.
- Alert status when available.
- Receiver name for delivery logs.
- Delivery result status.
- Retry attempt number.
- Error class or safe error message.

Logs must not include secret values.

Non-Goals
---------

- No UI.
- No manual configuration database.
- No container restart or remediation behavior.
- No Prometheus rule engine replacement.
- No hard dependency on Discord or any other receiver provider.
