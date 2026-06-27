Operations
==========

Status: initial operations guide

Purpose
-------

This document describes how to run DockerMonitor as a container
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
  --name docker-monitor \
  --group-add "$(stat -c '%g' /var/run/docker.sock)" \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/config:ro \
  -v ./secrets:/run/secrets:ro \
  -e CONFIG_FILE=/config/config.yaml \
  docker-monitor:latest
```

Docker Compose Example
----------------------

```yaml
services:
  docker-monitor:
    image: docker-monitor:latest
    container_name: docker-monitor
    restart: unless-stopped
    group_add:
      - "${DOCKER_SOCKET_GID:-0}"
    environment:
      CONFIG_FILE: /config/config.yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config:/config:ro
      - ./secrets:/run/secrets:ro
    healthcheck:
      test:
        ["CMD", "uv", "run", "--no-sync", "--no-dev", "docker-monitor", "healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

A complete Compose example is available at `examples/compose.yaml`, with a
matching config file at `examples/config.yaml`.
Set `DOCKER_SOCKET_GID=$(stat -c '%g' /var/run/docker.sock)` before using the
Compose example on systems where the socket is not group-readable by GID `0`.

Example Monitored Service
-------------------------

In label opt-in mode, monitored containers must include the configured monitor
label:

```yaml
services:
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    labels:
      docker-monitor.enable: "true"
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
uv run docker-monitor config-check --config /config/config.yaml
```

Run the service:

```sh
uv run docker-monitor run --config /config/config.yaml
```

The service installs `SIGTERM` and `SIGINT` handlers, reconciles startup state
before consuming live events, and logs JSON records to stdout.

Container validation commands:

```sh
docker build --target runtime -t docker-monitor:local .
docker run --rm docker-monitor:local healthcheck
docker compose -f examples/compose.yaml config
```

Published container images are pushed to GitHub Container Registry by the
publish workflow documented in `docs/release.md`.

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
uv run --no-sync --no-dev docker-monitor healthcheck
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

After reconnecting, startup reconciliation runs again before live event
consumption resumes.

Shutdown
--------

The service should handle `SIGTERM` and `SIGINT`.

Expected shutdown behavior:

- Stop consuming new Docker events.
- Finish the current receiver delivery path within the configured shutdown grace
  period and plugin HTTP timeouts.
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
