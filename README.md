# DockerMonitor

DockerMonitor watches Docker container health transitions and
routes normalized alerts to configured receiver plugins.

The implementation is tracked through `docs/task_tracker.md`. Contributor
guidance is in `AGENTS.md`.

Development commands use `uv`:

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

Validate a config file with:

```sh
uv run docker-monitor config-check --config /config/config.yaml
```

Run the monitor with:

```sh
uv run docker-monitor run --config /config/config.yaml
```

Release and CI behavior is documented in `docs/release.md`.
