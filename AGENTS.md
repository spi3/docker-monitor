# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python service, tests, docs, examples, and task
definitions. Core docs live in `docs/*.md`. Implementation tasks are tracked in
`docs/task_tracker.md`, with one task definition per file under `docs/tasks/`.

Main layout:

- `src/docker_monitor/`: Python service package.
- `src/docker_monitor/receivers/`: optional receiver plugins.
- `tests/`: unit, component, and end-to-end tests.

Keep Docker event logic, routing, and provider-specific receiver code separated
as described in `docs/architecture.md`.

## Build, Test, and Development Commands

Tooling is managed by `uv`. Use these commands:

- `uv sync`: install the project and development toolchain.
- `uv run pytest`: run the default test suite.
- `uv run pytest -m e2e`: run end-to-end tests.
- `uv run ruff check .`: run lint checks.
- `uv run ruff format --check .`: verify formatting.
- `uv run mypy .`: run type checks.

Record exact commands and results in the active task file before marking work
done.

CI runs the same Python gates through `uv`, plus package build, Compose
validation, container image builds, containerized e2e tests, and a runtime
healthcheck.

## Coding Style & Naming Conventions

Use Python 3.12+ and keep code typed where practical. Prefer small modules with
clear boundaries. Provider-specific formatting belongs only in receiver plugins.

Use snake_case for Python modules, functions, variables, and task filenames.
Task files use `NNNN-short-kebab-case-title.md`, for example
`docs/tasks/0001-project-scaffold-and-tooling.md`.

## Testing Guidelines

Default tests must not require a live Docker daemon or real receiver
credentials. Use fakes for Docker sources and local test doubles for receivers.
Add or update end-to-end tests for user-visible behavior, routing, delivery, and
runtime changes.

Before completion, run unit, component, end-to-end, lint, formatting, build, and
type-check gates when available.

## Commit & Pull Request Guidelines

Use Conventional Commits for every commit:

- `feat(task-0002): add configuration validation`
- `fix(task-0005): handle missing Docker health state`
- `docs(task-0004): record filtering acceptance evidence`

Each implementation task must finish with its own commit after acceptance
criteria pass and completion evidence is recorded. Pull requests should include
scope, linked task file, test evidence, documentation updates, and residual
risks.

Release commits update `[project].version` in `pyproject.toml`; semver release
tags use the matching `vX.Y.Z` format.

## Security & Configuration Tips

Prefer `*_file` secret inputs. Never log webhook URLs, auth headers, tokens, or
secret file contents. Treat Docker socket access as privileged, even when mounted
read-only.
