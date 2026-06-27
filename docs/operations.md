Operations
==========

Status: initial operations guide

Purpose
-------

This document describes how to run Docker Health Alert Monitor as a container
and what operators should expect at runtime.

Container Runtime
-----------------

The service is intended to run as a container next to the Docker workloads it
monitors.

Required mounts:

```text
/var/run/docker.sock:/var/run/docker.sock:ro
/path/to/config:/config:ro
```

Optional secret mounts:

```text
/path/to/secrets:/run/secrets:ro
```

Docker socket access is privileged even when mounted read-only. Treat any
container with Docker socket access as highly trusted.

Docker Run Example
------------------

```sh
docker run -d \
  --name docker-health-alerts \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/config:ro \
  -v ./secrets:/run/secrets:ro \
  -e CONFIG_FILE=/config/config.yaml \
  docker-health-alerts:latest
```

Docker Compose Example
----------------------

```yaml
services:
  docker-health-alerts:
    image: docker-health-alerts:latest
    container_name: docker-health-alerts
    restart: unless-stopped
    environment:
      CONFIG_FILE: /config/config.yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config:/config:ro
      - ./secrets:/run/secrets:ro
    healthcheck:
      test: ["CMD", "docker-health-alerts", "healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

Example Monitored Service
-------------------------

In label opt-in mode, monitored containers must include the configured monitor
label:

```yaml
services:
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    labels:
      docker-health-alert.enable: "true"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Configuration
-------------

The recommended config path in the container is:

```text
/config/config.yaml
```

The service should read `CONFIG_FILE` when provided. If `CONFIG_FILE` is not
set, it should use the default path.

Validate configuration before running the service:

```sh
uv run docker-health-alerts config-check --config /config/config.yaml
```

Secrets
-------

Prefer file-based secrets:

```yaml
receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: /run/secrets/discord_webhook
```

Secret files should be mounted read-only. The service should strip one trailing
newline from secret file values to support Docker secrets.

Healthcheck
-----------

The container should provide a healthcheck command.

Recommended command shape:

```sh
uv run --no-dev docker-health-alerts healthcheck
```

The command should return:

- Exit code `0` when the process is healthy.
- Non-zero when configuration failed, receiver initialization failed, or the
  event loop is no longer running.

If a future HTTP health endpoint is added, it should be bound to localhost by
default unless explicitly configured otherwise.

Structured Logs
---------------

The service logs JSON to stdout.

Example:

```json
{
  "time": "2026-06-27T17:00:00Z",
  "level": "info",
  "event": "alert.delivered",
  "container_id": "abc123",
  "container_name": "qbittorrent",
  "alert_status": "firing",
  "receiver": "discord-lab",
  "delivery_status": "success",
  "attempt": 1
}
```

Logs must be safe to collect in centralized logging systems. They must not
contain webhook URLs, tokens, authorization headers, or secret file contents.

Reconnects
----------

The service should reconnect after Docker event stream disconnects.

Expected behavior:

- Log the disconnect with a safe error summary.
- Back off before reconnecting.
- Reconnect to Docker.
- Reconcile current container health state.
- Resume consuming live events.

This keeps alerts accurate across Docker daemon restarts and temporary socket
interruptions.

Shutdown
--------

The service should handle `SIGTERM` and `SIGINT`.

Expected shutdown behavior:

- Stop consuming new Docker events.
- Finish in-flight receiver deliveries within a bounded grace period.
- Cancel pending retries after the grace period.
- Flush logs.
- Exit with status code `0` for normal shutdown.

Common Failure Modes
--------------------

Configuration validation failure:

- Service exits before consuming Docker events.
- Logs identify the invalid field and receiver or route when applicable.

Missing configured plugin:

- Service exits during startup.
- Logs name the missing plugin without importing unrelated plugins.

Unreadable secret file:

- Service exits during receiver initialization.
- Logs the file path and receiver name, but not secret contents.

Docker socket unavailable:

- Service logs connection failure.
- Startup may fail or retry depending on implementation configuration.

Receiver delivery failure:

- Service logs the receiver, attempt, and safe error summary.
- Other receivers still run.
- Docker event loop continues unless the receiver or route is fatal.

Upgrade Notes
-------------

The alert schema includes a `version` field. Breaking changes to the normalized
alert object should increment the schema version and be documented in release
notes.
