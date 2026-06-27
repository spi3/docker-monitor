Task 0011: GitHub Actions CI, Publishing, And Versioning
========================================================

Tracker: `docs/task_tracker.md`

Objective
---------

Add GitHub Actions automation for build, lint, formatting, typing, tests,
container image publishing to GitHub Container Registry, and release versioning.

Related Docs
------------

- `AGENTS.md`
- `docs/operations.md`
- `docs/testing.md`
- `docs/tech_stack.md`
- `docs/task_acceptance_criteria.md`

Scope
-----

- Create GitHub Actions workflows for pull request and main branch validation.
- Run all Python gates through `uv`.
- Validate package build.
- Validate container image build.
- Publish container images to GitHub Container Registry.
- Define image tag strategy for branches, commits, and releases.
- Define project versioning strategy and release process.
- Configure least-privilege workflow permissions.
- Document CI, publishing, and versioning behavior.

Out Of Scope
------------

- Publishing to registries other than GitHub Container Registry.
- Signing images or generating SBOMs unless added as explicit follow-up scope.
- Multi-architecture builds unless explicitly added during implementation.

Dependencies
------------

- 0010

Implementation Notes
--------------------

Use `uv` for every Python command in GitHub Actions. Publishing should target
GitHub Container Registry, normally `ghcr.io/<owner>/<repository>`. Image tags
should include immutable commit SHA tags and release semver tags.

Task-Specific Acceptance Criteria
---------------------------------

- Pull request workflow runs `uv sync`, tests, lint, formatting, type checks,
  and package build.
- End-to-end tests run in CI without real receiver credentials.
- Container image build is validated in CI.
- Main branch or release workflow publishes to GitHub Container Registry.
- Published images include commit SHA tags.
- Semver release tags produce matching image tags.
- `latest` is published only from the default branch or explicit release flow.
- Workflow permissions are scoped to the minimum required for checkout,
  packages, and attestations if used.
- Version source of truth is documented.
- Contributor and operations docs describe the CI and release commands.

Universal Acceptance Criteria
-----------------------------

All criteria in `docs/task_acceptance_criteria.md` apply.

Completion Evidence
-------------------

Completed after Task 0010.

Implemented artifacts:

- `.github/workflows/ci.yaml` for pull requests and `main` branch pushes.
- `.github/workflows/publish-image.yaml` for GHCR publishing from `main` and
  semver release tags.
- `docs/release.md` documenting version source of truth, CI gates, publishing,
  image tags, release steps, and workflow permissions.
- `tests/test_github_workflows.py` covering required CI commands, workflow
  permissions, GHCR publishing, immutable SHA tags, semver tags, and
  default-branch-only `latest`.
- Updates to `AGENTS.md`, `README.md`, `docs/operations.md`,
  `docs/testing.md`, and `docs/tech_stack.md`.

Commands run:

```sh
uv --cache-dir .uv-cache run pytest
uv --cache-dir .uv-cache run pytest -m e2e
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run ruff format --check .
uv --cache-dir .uv-cache run mypy .
uv --cache-dir .uv-cache build
docker compose -f examples/compose.yaml config
docker build --target runtime -t docker-monitor:ci .
docker build --target test -t docker-monitor:test .
docker run --rm docker-monitor:test
docker run --rm docker-monitor:ci healthcheck
```

Results:

- Unit/component test gate passed: 102 tests passed.
- End-to-end gate passed locally: 2 selected tests passed.
- Ruff lint passed.
- Ruff formatting check passed.
- Mypy strict type check passed.
- Package build produced source distribution and wheel.
- Compose config validation passed.
- Runtime image build passed.
- Test image build passed.
- Containerized end-to-end tests passed: 2 selected tests passed.
- Runtime container healthcheck returned `{"status": "ok"}`.
- The first sandboxed package build attempt failed due blocked network access for
  the isolated build backend; rerunning the same `uv build` with approved
  network access passed.

Document sweep:

- Added `docs/release.md`.
- Updated `AGENTS.md`, `README.md`, `docs/operations.md`, `docs/testing.md`,
  and `docs/tech_stack.md`.
- Checked `docs/security.md`, `docs/requirements.md`,
  `docs/task_acceptance_criteria.md`, and `docs/implementation_plan.md`; no
  further changes were required.
- Updated `docs/task_tracker.md` status.

Maintainability sweep:

- CI commands use the same `uv` gates as local development.
- Publishing is isolated to a separate workflow with `packages: write`; CI uses
  read-only repository permissions.
- Version source of truth is documented as `[project].version` in
  `pyproject.toml`.
- Workflow expectations are tested in the normal unit test suite.

Residual risk:

- Workflows have not run on GitHub in this local environment. Local workflow
  structure, commands, Docker builds, and container commands were validated.
