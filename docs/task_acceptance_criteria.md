Task Acceptance Criteria
========================

Status: active acceptance standard

Purpose
-------

This document defines the acceptance criteria every implementation task must
satisfy before it can be marked `done`. It also records task-specific criteria
for the initial implementation backlog.

Universal Acceptance Criteria
-----------------------------

Every task must satisfy all criteria in this section.

Functional completion:

- The task objective is implemented as described in its task file.
- All in-scope behavior has automated test coverage.
- Out-of-scope behavior is not introduced accidentally.
- Public behavior matches the relevant docs.

Full end-to-end testing:

- The full end-to-end test suite runs and passes before task completion.
- If the task introduces new user-visible behavior, container runtime behavior,
  routing behavior, or receiver behavior, the end-to-end suite is extended to
  cover it.
- End-to-end tests must not require real receiver credentials.
- Docker-dependent end-to-end tests should use explicit markers so they can be
  run intentionally.

Best practices:

- Changes follow the architecture boundaries documented in
  `docs/architecture.md`.
- Provider-specific logic remains inside receiver plugins.
- Core Docker event handling remains provider-neutral.
- Secrets are not logged, returned in delivery results, or captured in test
  snapshots.
- Errors are actionable and safe to log.
- Configuration remains file-based and GitOps-friendly.

Full document sweep:

- All docs in `docs/` are checked for impact.
- Any document affected by behavior, configuration, command, security, or
  operational changes is updated.
- The active task file records which docs were updated or explicitly checked.
- `docs/task_tracker.md` is updated when status changes.

Maintainability sweep:

- Module boundaries are clear.
- Duplicate logic is removed or justified.
- Complex code has focused tests.
- Interfaces are narrow and typed where practical.
- New dependencies are justified and documented.
- Code remains testable without a live Docker daemon unless the task is an
  explicit Docker integration task.

Build, lint, formatting, and test gates:

- Build checks pass.
- Lint checks pass.
- Formatting checks pass.
- Unit tests pass.
- Component tests pass.
- End-to-end tests pass.
- Type checks pass once type checking is configured.

Git finalization:

- The task is committed to Git before the next task begins.
- The commit message follows Conventional Commits: `type(scope): summary`.
- The scope should be the task ID, for example `task-0006`.
- The commit includes implementation, tests, docs, tracker updates, and
  completion evidence for that task.
- The task file records the final commit hash.

Completion evidence:

- Exact commands run are recorded in the task file.
- Test results are recorded in the task file.
- Documentation updates are recorded in the task file.
- Final commit hash is recorded in the task file.
- Any residual risk is recorded in the task file.

Task-Specific Criteria
----------------------

The criteria below supplement the universal criteria. A task is complete only
when both universal and task-specific criteria are satisfied.

Task 0001: Project Scaffold And Tooling
---------------------------------------

Task file:

```text
docs/tasks/0001-project-scaffold-and-tooling.md
```

Acceptance criteria:

- Python package layout is created.
- Runtime entry point exists.
- Dependency management is configured.
- Test framework is configured.
- Lint, format, and type-check commands are documented.
- A minimal smoke test exists.
- A minimal end-to-end test command exists, even if it initially validates only
  CLI startup or healthcheck behavior.
- Dockerfile or container build plan is present.

Task 0002: Configuration Model And Validation
---------------------------------------------

Task file:

```text
docs/tasks/0002-configuration-model-and-validation.md
```

Acceptance criteria:

- YAML configuration loading is implemented.
- Defaults match `docs/configuration.md`.
- Monitor mode validation rejects invalid values.
- Receiver names must be unique.
- Route receiver references are validated.
- Unknown configured plugins fail startup clearly.
- Duration parsing is tested.
- Secret file validation behavior is defined and tested.
- Configuration docs are updated with any final field names.

Task 0003: Alert Model, Redaction, And Normalization
----------------------------------------------------

Task file:

```text
docs/tasks/0003-alert-model-redaction-and-normalization.md
```

Acceptance criteria:

- Normalized alert schema version `1` is implemented.
- Container, Compose, label, event, and health log fields are populated.
- Sensitive labels are redacted case-insensitively.
- Healthcheck output is truncated according to configuration.
- Alert statuses map correctly from Docker health states.
- Provider plugins receive normalized alert objects only.
- Schema behavior is documented if implementation details differ from examples.

Task 0004: Monitor Filtering And Health State Tracking
------------------------------------------------------

Task file:

```text
docs/tasks/0004-monitor-filtering-and-health-state-tracking.md
```

Acceptance criteria:

- `label_opt_in` and `label_opt_out` modes are implemented.
- Optional name, image, Compose project, Compose service, and arbitrary label
  filters are implemented.
- State is tracked by full container ID.
- Duplicate unchanged health states are suppressed.
- Disabled `send_resolved` and `send_starting` settings still update state.
- Filtering and state behavior are covered by unit tests.

Task 0005: Docker Source Adapter And Startup Reconciliation
----------------------------------------------------------

Task file:

```text
docs/tasks/0005-docker-source-adapter-and-startup-reconciliation.md
```

Acceptance criteria:

- Docker client connects through socket or `DOCKER_HOST`.
- Existing containers can be inspected.
- Containers without healthchecks are ignored.
- Startup reconciliation emits firing alerts for already unhealthy monitored
  containers.
- Healthy containers initialize state without alerting.
- Starting containers alert only when `send_starting` is enabled.
- Live event stream subscribes with container `health_status` filters.
- Source adapter can be tested with fakes without a live Docker daemon.

Task 0006: Routing, Delivery Coordination, And Retries
------------------------------------------------------

Task file:

```text
docs/tasks/0006-routing-delivery-coordination-and-retries.md
```

Acceptance criteria:

- Routes match normalized alert fields.
- Multiple receivers per route are supported.
- No-match alerts are logged and dropped without error.
- Delivery result statuses drive retry behavior.
- Retry attempts are bounded and logged.
- Permanent failures are not retried.
- Receiver failures do not stop other receivers unless fatal behavior is
  configured.
- Delivery logs are structured and secret-safe.

Task 0007: Generic Webhook Plugin
---------------------------------

Task file:

```text
docs/tasks/0007-generic-webhook-plugin.md
```

Acceptance criteria:

- Plugin loads only when configured.
- `url` and `url_file` are supported.
- Custom headers and header file values are supported.
- Normalized alert object is sent as default JSON payload.
- Optional JSON payload template behavior is implemented or explicitly deferred
  with documented scope.
- Network failures and non-2xx responses are retryable.
- 2xx responses are successful.
- Webhook URLs and secret headers are redacted from logs.

Task 0008: Discord Plugin
-------------------------

Task file:

```text
docs/tasks/0008-discord-plugin.md
```

Acceptance criteria:

- Plugin loads only when configured.
- `webhook_url` and `webhook_url_file` are supported.
- Firing messages identify unhealthy containers.
- Resolved messages identify recovered containers.
- Starting messages are handled when emitted by core.
- Discord webhook URL is never logged.
- Network failures and Discord 5xx responses are retryable.
- Discord payload formatting is covered by tests without real credentials.

Task 0009: Runtime Loop, Reconnects, Shutdown, And Healthcheck
-------------------------------------------------------------

Task file:

```text
docs/tasks/0009-runtime-loop-reconnects-shutdown-and-healthcheck.md
```

Acceptance criteria:

- Main service loop runs startup reconciliation before live event consumption.
- Docker event stream disconnects trigger bounded reconnect behavior.
- Reconciliation runs after reconnect.
- `SIGTERM` and `SIGINT` trigger graceful shutdown.
- In-flight deliveries receive a bounded grace period.
- Healthcheck command or endpoint is implemented.
- Structured JSON logs are emitted to stdout.

Task 0010: Container Packaging, Examples, And Full System Validation
-------------------------------------------------------------------

Task file:

```text
docs/tasks/0010-container-packaging-examples-and-full-system-validation.md
```

Acceptance criteria:

- Container image builds successfully.
- Runtime image uses only required runtime dependencies.
- Config and secret mount examples work.
- Docker Compose example is updated and validated.
- Full end-to-end suite passes in containerized form.
- Security documentation reflects final runtime behavior.
- Operations documentation includes final commands and healthcheck behavior.
- Release readiness evidence is recorded.

Task 0011: GitHub Actions CI, Publishing, And Versioning
--------------------------------------------------------

Task file:

```text
docs/tasks/0011-github-actions-ci-publishing-and-versioning.md
```

Acceptance criteria:

- GitHub Actions workflow runs build, lint, formatting, type-check, unit,
  component, and end-to-end gates through `uv`.
- Workflow validates the container image build.
- Workflow publishes container images to GitHub Container Registry.
- Published image tags include an immutable commit SHA tag.
- Release tags publish semver image tags.
- `latest` is published only from the default branch or explicit release flow.
- Workflow permissions follow least privilege.
- Package/version metadata has a documented single source of truth.
- Release/versioning documentation is updated.
- CI behavior is documented in contributor and operations docs.
