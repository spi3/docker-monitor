Task 0008: Discord Plugin
=========================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement the optional `discord` receiver plugin and Discord-friendly alert
message formatting.

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
- Support `webhook_url` and `webhook_url_file`.
- Format firing messages.
- Format resolved messages.
- Support starting messages when the core emits them.
- Classify Discord HTTP and network delivery results.
- Redact Discord webhook URLs from logs.

Out Of Scope
------------

- Slack, ntfy, Gotify, SMTP, or Pushover plugins.
- Core alert state transitions.
- Docker event handling.

Dependencies
------------

- 0006

Implementation Notes
--------------------

Discord-specific formatting must stay inside this plugin. Tests should not use
real Discord credentials.

Task-Specific Acceptance Criteria
---------------------------------

- Plugin is imported only when referenced by configuration.
- Webhook URL file loading strips one trailing newline.
- Firing payloads clearly identify unhealthy containers.
- Resolved payloads clearly identify recovered containers.
- Starting payloads are handled without changing core routing.
- 2xx responses return success.
- Network failures and Discord 5xx responses are retryable.
- Webhook URL redaction is covered by tests.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0007.

Implemented artifacts:

- `docker_monitor/receivers/discord.py` with optional plugin loading via
  the shared registry, `webhook_url`/`webhook_url_file`,
  `WEBHOOK_URL`/`WEBHOOK_URL_FILE`, Discord-friendly payload formatting, and
  HTTP delivery classification.
- Discord payloads for `firing`, `resolved`, and `starting` statuses.
- Retryable classification for network failures, HTTP 429, and HTTP 5xx.
- Permanent classification for other HTTP 4xx responses.
- `tests/test_discord.py` covering webhook file newline stripping, firing,
  resolved, starting, HTTP posting, retryable failures, permanent failures, and
  webhook URL redaction in failure messages.
- Updated registry missing-plugin tests now that Discord exists.

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

- Unit/component test gate passed: 94 tests passed.
- End-to-end gate passed: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.
- The first sandboxed build attempt failed due blocked network access for the
  isolated build backend; rerunning the same `uv build` with approved network
  access passed.

Document sweep:

- Updated `docs/plugin_contract.md` with Discord 429/5xx retryable behavior and
  other 4xx permanent behavior.
- Checked `docs/configuration.md`, `docs/security.md`, `docs/testing.md`, and
  `docs/requirements.md`; no additional updates were needed.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- Discord-specific formatting is isolated in `receivers/discord.py`.
- The plugin does not inspect Docker SDK objects or alter routing/state logic.
- Webhook URLs are never included in delivery result messages.
- Tests use `httpx.MockTransport` and require no real Discord credentials.

Residual risk:

- Runtime loop integration happens in Task 0009.
