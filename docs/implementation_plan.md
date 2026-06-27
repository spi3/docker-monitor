Implementation Plan
===================

Status: active planning process

Purpose
-------

This document defines how implementation work is created, tracked, executed,
verified, and completed. The process is intentionally file-based so the project
can be managed in Git without a separate task database.

Task Artifacts
--------------

Implementation work is tracked through these artifacts:

- `docs/task_tracker.md`: The single task tracker. It records task status,
  summary, dependencies, and the task definition file location.
- `docs/tasks/`: Directory containing one task definition file per task.
- `docs/task_acceptance_criteria.md`: Universal and task-specific acceptance
  criteria.

Each implementation task must be defined in its own file. The tracker must link
to that file instead of embedding the full task definition.

Task File Naming
----------------

Task files use this naming pattern:

```text
docs/tasks/NNNN-short-kebab-case-title.md
```

Examples:

```text
docs/tasks/0001-project-scaffold-and-tooling.md
docs/tasks/0002-configuration-model.md
```

Task IDs are permanent. If a task is removed, its ID should not be reused.

Task Statuses
-------------

Use these statuses in `docs/task_tracker.md`:

- `proposed`: The task is known but not ready to start.
- `ready`: The task is defined and has no blocking dependencies.
- `in_progress`: Implementation is actively underway.
- `blocked`: Work cannot continue without a decision or external dependency.
- `review`: Implementation is complete and awaiting verification or review.
- `done`: All acceptance criteria are satisfied and evidence is recorded.

Only the tracker records current status. Task files describe scope and
acceptance, but should not be treated as the source of truth for current status.

Task Definition Structure
-------------------------

Each task definition file should include:

- Task ID and title.
- Tracker location.
- Related docs.
- Objective.
- Scope.
- Out of scope.
- Dependencies.
- Implementation notes.
- Task-specific acceptance criteria.
- Universal acceptance criteria reference.
- Completion evidence section.

The completion evidence section is filled when the task moves to `done`.

Creating A Task
---------------

To create a task:

1. Pick the next unused numeric task ID.
2. Create a task definition file under `docs/tasks/`.
3. Define the objective, scope, out-of-scope work, dependencies, and
   task-specific acceptance criteria.
4. Add or update the task-specific acceptance criteria in
   `docs/task_acceptance_criteria.md`.
5. Add a row to `docs/task_tracker.md`.
6. Set the status to `proposed` or `ready`.
7. Sweep related docs for consistency.

Tasks should be small enough to complete with high confidence, but large enough
to produce a coherent user-visible or architecture-visible increment.

Starting A Task
---------------

Before implementation begins:

1. Read the task definition file.
2. Read linked docs and requirements.
3. Confirm dependencies are `done`.
4. Move the task status to `in_progress` in `docs/task_tracker.md`.
5. Identify the expected code, test, config, and documentation changes.

If the task definition is stale, update the task file and acceptance criteria
before implementation starts.

Implementing A Task
-------------------

Implementation should follow the existing architecture boundaries:

- Docker observation stays in the Docker source adapter.
- Filtering and state transitions stay in core modules.
- Provider-specific formatting stays in receiver plugins.
- Routing uses normalized alert objects.
- Secret redaction is enforced before logs or receiver output can leak values.

Keep changes scoped to the active task. If unrelated work is discovered, create
a separate task instead of expanding scope silently.

Task Completion
---------------

A task can move to `done` only after:

1. All task-specific acceptance criteria are satisfied.
2. All universal acceptance criteria in `docs/task_acceptance_criteria.md` are
   satisfied.
3. Full end-to-end testing required by the acceptance criteria has run and
   passed.
4. Build, lint, formatting, and test commands have run and passed.
5. A full documentation sweep has been performed and relevant docs are updated.
6. A maintainability sweep has been performed.
7. Completion evidence is recorded in the task file.
8. The tracker status is updated to `done`.
9. The finalized task is committed to Git with a Conventional Commit message.

Completion evidence should include exact commands run, test outcomes, changed
docs, commit hash, and any residual risk.

Git And Commit Discipline
-------------------------

This repository uses Git for all implementation tracking. Every implementation
task must end with a dedicated commit after all task-specific and universal
acceptance criteria are satisfied.

Commit rules:

- Use Conventional Commits: `type(scope): summary`.
- Use the task ID as the scope for task work, for example
  `feat(task-0003): add normalized alert model`.
- Keep each task's implementation, tests, docs, tracker update, and completion
  evidence in that task's commit.
- Do not begin the next task until the previous task has a passing task commit.
- Record the task commit hash in the task file completion evidence.
- If follow-up fixes are needed before moving on, amend the task commit or add a
  clearly related Conventional Commit with the same task scope.

Allowed commit types:

- `build`
- `chore`
- `ci`
- `docs`
- `feat`
- `fix`
- `perf`
- `refactor`
- `revert`
- `style`
- `test`

The repository includes a local commit-msg hook under `.githooks/` to reject
non-conventional commit messages when `core.hooksPath` is configured.

Document Sweep
--------------

Every task must check whether these documents need updates:

- `docs/vision.md`
- `docs/requirements.md`
- `docs/tech_stack.md`
- `docs/architecture.md`
- `docs/configuration.md`
- `docs/plugin_contract.md`
- `docs/operations.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/implementation_plan.md`
- `docs/task_acceptance_criteria.md`
- `docs/task_tracker.md`
- Active task definition files under `docs/tasks/`
- Git commit history for completed task commits

The sweep should update docs when behavior, configuration, commands, security
posture, or operating expectations change.

Maintainability Sweep
---------------------

Every task must include a maintainability sweep before completion:

- Confirm module boundaries remain clean.
- Remove unnecessary duplication.
- Keep public interfaces narrow and documented.
- Keep tests readable and close to the behavior they verify.
- Confirm provider-specific code has not leaked into the core engine.
- Confirm secret-handling code is centralized or consistently applied.
- Confirm errors are clear and actionable.

Testing Expectations
--------------------

The default test suite should not require a live Docker daemon or real receiver
credentials. Full end-to-end testing should use fakes, local test servers, or
controlled fixtures unless a task explicitly opts into Docker integration
testing.

When Docker integration tests are added, they should be marked separately so
they can be run intentionally.

Recommended test command groups:

```sh
uv sync
uv run pytest
uv run pytest -m e2e
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

The exact commands are established by the tooling task and should be kept
current in task completion evidence.

Splitting Tasks
---------------

Split a task when:

- It crosses multiple major architecture boundaries.
- It cannot be reviewed coherently.
- It requires unrelated decisions.
- Its acceptance criteria become too broad to verify directly.

When splitting, keep the original task as the parent planning reference or close
it with evidence explaining the split. New task IDs should be assigned to the
child tasks.

Changing Task Scope
-------------------

If implementation reveals that a task definition is wrong or incomplete:

1. Update the task file.
2. Update `docs/task_acceptance_criteria.md` if acceptance changes.
3. Update `docs/task_tracker.md` if status, dependencies, or summary changes.
4. Record the reason in the task file.

Scope changes should be explicit so future review can distinguish planned work
from incidental changes.

Initial Implementation Sequence
-------------------------------

The initial task sequence is:

1. Project scaffold and tooling.
2. Configuration model and validation.
3. Alert model, redaction, and normalization.
4. Monitor filtering and health state tracking.
5. Docker source adapter and startup reconciliation.
6. Routing, delivery coordination, and retries.
7. Generic webhook plugin.
8. Discord plugin.
9. Runtime loop, reconnects, shutdown, and healthcheck.
10. Container packaging, examples, and full system validation.
11. GitHub Actions CI, container publishing, and versioning.

The tracker is the source of truth for current status and dependency ordering.
