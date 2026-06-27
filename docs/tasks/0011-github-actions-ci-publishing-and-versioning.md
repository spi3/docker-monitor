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

Completion evidence is recorded here when the task moves to `done`.
