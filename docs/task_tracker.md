Task Tracker
============

Status: active task tracker

Purpose
-------

This file is the single status tracker for implementation tasks. Each task is
defined in its own file under `docs/tasks/`.

Statuses
--------

- `proposed`: Known task, not ready to start.
- `ready`: Defined and unblocked.
- `in_progress`: Active implementation.
- `blocked`: Waiting on a decision or external dependency.
- `review`: Implementation complete, verification pending.
- `done`: Acceptance criteria satisfied and evidence recorded.

Tracker
-------

| ID | Status | Task Definition | Summary | Dependencies |
| --- | --- | --- | --- | --- |
| 0001 | done | [Project Scaffold And Tooling](tasks/0001-project-scaffold-and-tooling.md) | Create Python package, tooling, tests, and initial runtime entry point. | None |
| 0002 | done | [Configuration Model And Validation](tasks/0002-configuration-model-and-validation.md) | Implement YAML config loading, defaults, validation, and route checks. | 0001 |
| 0003 | done | [Alert Model, Redaction, And Normalization](tasks/0003-alert-model-redaction-and-normalization.md) | Implement normalized alert schema, label redaction, and health log truncation. | 0001, 0002 |
| 0004 | done | [Monitor Filtering And Health State Tracking](tasks/0004-monitor-filtering-and-health-state-tracking.md) | Implement label modes, optional filters, state tracking, and duplicate suppression. | 0002, 0003 |
| 0005 | done | [Docker Source Adapter And Startup Reconciliation](tasks/0005-docker-source-adapter-and-startup-reconciliation.md) | Implement Docker adapter, startup inspection, reconciliation, and event subscription. | 0003, 0004 |
| 0006 | done | [Routing, Delivery Coordination, And Retries](tasks/0006-routing-delivery-coordination-and-retries.md) | Implement route matching, receiver dispatch, delivery results, and retry handling. | 0002, 0003 |
| 0007 | done | [Generic Webhook Plugin](tasks/0007-generic-webhook-plugin.md) | Implement generic HTTP webhook receiver plugin. | 0006 |
| 0008 | done | [Discord Plugin](tasks/0008-discord-plugin.md) | Implement Discord receiver plugin and message formatting. | 0006 |
| 0009 | done | [Runtime Loop, Reconnects, Shutdown, And Healthcheck](tasks/0009-runtime-loop-reconnects-shutdown-and-healthcheck.md) | Implement main event loop, reconnect behavior, graceful shutdown, and healthcheck. | 0005, 0006, 0007, 0008 |
| 0010 | done | [Container Packaging, Examples, And Full System Validation](tasks/0010-container-packaging-examples-and-full-system-validation.md) | Finalize image packaging, deployment examples, and full system validation. | 0009 |
| 0011 | done | [GitHub Actions CI, Publishing, And Versioning](tasks/0011-github-actions-ci-publishing-and-versioning.md) | Add GitHub Actions gates, GHCR image publishing, and release versioning. | 0010 |

Tracker Update Rules
--------------------

- Update status when work starts, blocks, enters review, or completes.
- Do not duplicate full task scope in this tracker.
- Keep dependencies accurate when tasks are split or reordered.
- A task can move to `done` only when its task file records completion evidence.
