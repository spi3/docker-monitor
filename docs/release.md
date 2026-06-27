Release And Versioning
======================

Status: initial release process

Version Source Of Truth
-----------------------

The package version in `pyproject.toml` under `[project].version` is the source
of truth for release versioning.

Release tags must match that version with a leading `v`.

Example:

```text
pyproject.toml version: 0.1.0
release tag: v0.1.0
```

CI
--

The CI workflow at `.github/workflows/ci.yaml` runs on pull requests and pushes
to `main`.

It runs:

- `uv sync --locked --python 3.12`
- `uv run pytest`
- `uv run pytest -m e2e`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy .`
- `uv build`
- Docker Compose example validation.
- Runtime image build.
- Test image build.
- Containerized end-to-end tests.
- Runtime container healthcheck.

Publishing
----------

The publish workflow at `.github/workflows/publish-image.yaml` publishes the
runtime image to GitHub Container Registry.

It runs on:

- Pushes to `main`.
- Semver release tags matching `v*.*.*`.

Image Tag Strategy
------------------

Published images include:

- Immutable commit SHA tags with the `sha-` prefix.
- Branch tags for branch pushes.
- Semver tags for release tags, such as `0.1.0` and `0.1`.
- `latest` only from the default branch.

Release Steps
-------------

1. Update `[project].version` in `pyproject.toml`.
2. Update release notes or documentation when behavior changed.
3. Run the full local gate suite documented in `docs/testing.md`.
4. Commit the version change.
5. Create and push a matching semver tag, for example `v0.1.0`.
6. Confirm the publish workflow completes and the GHCR image tags are present.

Permissions
-----------

The CI workflow uses read-only repository permissions. The publish workflow uses
`contents: read` and `packages: write`, which are the minimum permissions needed
to check out code and publish to GitHub Container Registry.
