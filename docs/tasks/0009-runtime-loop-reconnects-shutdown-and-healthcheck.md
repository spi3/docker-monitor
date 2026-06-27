Task 0009: Runtime Loop, Reconnects, Shutdown, And Healthcheck
==============================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Implement the main service runtime loop, reconnect behavior, graceful shutdown,
and healthcheck command or endpoint.

Related Docs
------------

- `docs/architecture.md`
- `docs/operations.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Run startup reconciliation before live event consumption.
- Consume Docker health events continuously.
- Reconnect after Docker stream disconnects.
- Reconcile after reconnect.
- Handle `SIGTERM` and `SIGINT`.
- Give in-flight deliveries a bounded grace period.
- Provide healthcheck command or endpoint.
- Emit structured JSON logs to stdout.

Out Of Scope
------------

- New receiver plugins.
- New monitor filter types.
- UI or metrics endpoint.

Dependencies
------------

- 0005
- 0006
- 0007
- 0008

Implementation Notes
--------------------

The event loop should isolate receiver failures from Docker event consumption
unless fatal behavior is configured.

Task-Specific Acceptance Criteria
---------------------------------

- Startup sequence matches `docs/architecture.md`.
- Reconnect behavior uses bounded backoff.
- Reconciliation runs after reconnect.
- Shutdown path stops new event consumption.
- In-flight delivery grace period is tested.
- Healthcheck behavior is documented and tested.
- JSON logs include stable operational fields.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completion evidence is recorded here when the task moves to `done`.
