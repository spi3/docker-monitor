# DockerMonitor

DockerMonitor watches Docker container health transitions and
routes normalized alerts to configured receiver plugins.

It runs as a small container, reads Docker health events from the Docker socket,
normalizes state changes, and sends alerts through configured receiver plugins.

## Run With Docker

Build a local image:

```sh
docker build --target runtime -t docker-monitor:local .
```

Run the container with a read-only Docker socket, a config file, and optional
secret mounts:

```sh
docker run -d \
  --name docker-monitor \
  --restart unless-stopped \
  --group-add "$(stat -c '%g' /var/run/docker.sock)" \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v "$PWD/examples/config.yaml:/config/config.yaml:ro" \
  -v "$PWD/examples/secrets:/run/secrets:ro" \
  -e CONFIG_FILE=/config/config.yaml \
  docker-monitor:local
```

Docker socket access is privileged even when mounted read-only. Run this
container only on hosts where DockerMonitor should be trusted with Docker API
visibility.

## Docker Compose

Use the checked-in example as a starting point:

```sh
DOCKER_SOCKET_GID="$(stat -c '%g' /var/run/docker.sock)" \
  docker compose -f examples/compose.yaml up -d --build
```

The Compose example mounts:

- `/var/run/docker.sock` read-only for Docker events and inspection.
- `examples/config.yaml` as `/config/config.yaml`.
- `examples/secrets/` as `/run/secrets/`.

Check the container health command:

```sh
docker run --rm docker-monitor:local healthcheck
```

## Configuration

DockerMonitor uses a YAML config file. Set `CONFIG_FILE` or pass
`--config /path/to/config.yaml`.

Minimal Discord example:

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

routes:
  - match:
      severity: warning
    receivers:
      - discord-lab
```

Generic webhook example:

```yaml
receivers:
  - name: raw-webhook
    plugin: generic-webhook
    config:
      url_file: /run/secrets/webhook_url
      timeout: 10s
      retries: 3
      headers:
        X-Source: docker-monitor

routes:
  - match:
      severity: warning
    receivers:
      - raw-webhook
```

Default monitoring is opt-in. Add this label to containers that should be
watched:

```yaml
labels:
  docker-monitor.enable: "true"
```

Use `label_opt_out` to monitor all containers except those labeled
`docker-monitor.enable=false`.

Validate configuration before running:

```sh
docker run --rm \
  -v "$PWD/examples/config.yaml:/config/config.yaml:ro" \
  -v "$PWD/examples/secrets:/run/secrets:ro" \
  docker-monitor:local config-check --config /config/config.yaml
```

Secrets should normally use `*_file` settings mounted from Docker secrets,
bind-mounted files, or another secret manager. Do not put webhook URLs or auth
headers in logs, Compose labels, or committed config files.

More configuration details are in `docs/configuration.md`.

## Development

Development commands use `uv`:

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

Run the monitor with:

```sh
uv run docker-monitor run --config ./config.yaml
```

The implementation is tracked through `docs/task_tracker.md`. Contributor
guidance is in `AGENTS.md`.

Release and CI behavior is documented in `docs/release.md`.
