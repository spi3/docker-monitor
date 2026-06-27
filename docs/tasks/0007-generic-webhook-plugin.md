Task 0007: Generic Webhook Plugin
=================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement the optional `generic-webhook` receiver plugin.

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
- Support `url` and `url_file`.
- Support custom headers.
- Support header values loaded from files.
- Send normalized alert object as JSON by default.
- Classify HTTP and network delivery results.
- Redact URLs and secret headers from logs.

Out Of Scope
------------

- Discord formatting.
- Docker event handling.
- Third-party webhook provider-specific transforms.

Dependencies
------------

- 0006

Implementation Notes
--------------------

The plugin should use the shared delivery result contract. Secret values loaded
from files must not appear in exceptions, logs, or test snapshots.

Task-Specific Acceptance Criteria
---------------------------------

- Plugin is imported only when referenced by configuration.
- URL file loading strips one trailing newline.
- Static and file-loaded headers are applied.
- Default request body is the normalized alert object.
- 2xx responses return success.
- Network errors and non-2xx responses are retryable by default.
- Secret redaction tests cover URLs and header values.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completion evidence is recorded here when the task moves to `done`.
