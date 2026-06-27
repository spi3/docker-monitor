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

Completion evidence is recorded here when the task moves to `done`.
