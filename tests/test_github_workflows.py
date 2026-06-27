from __future__ import annotations

from pathlib import Path

import yaml


def workflow_text(name: str) -> str:
    return Path(".github/workflows", name).read_text(encoding="utf-8")


def test_ci_workflow_runs_required_uv_and_container_gates() -> None:
    text = workflow_text("ci.yaml")

    for command in [
        "uv sync --locked --python 3.12",
        "uv run pytest",
        "uv run pytest -m e2e",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run mypy .",
        "uv build",
        "docker compose -f examples/compose.yaml config",
        "docker build --target runtime",
        "docker build --target test",
        "docker run --rm docker-monitor:test",
        "docker run --rm docker-monitor:ci healthcheck",
    ]:
        assert command in text

    parsed = yaml.safe_load(text)
    assert parsed["permissions"] == {"contents": "read"}


def test_publish_workflow_publishes_ghcr_with_expected_tags_and_permissions() -> None:
    text = workflow_text("publish-image.yaml")
    parsed = yaml.safe_load(text)

    assert parsed["permissions"] == {"contents": "read", "packages": "write"}
    assert "ghcr.io/${{ github.repository }}" in text
    assert "type=sha,prefix=sha-" in text
    assert "type=semver,pattern={{version}}" in text
    assert "type=semver,pattern={{major}}.{{minor}}" in text
    assert "type=raw,value=latest,enable={{is_default_branch}}" in text
    assert "target: runtime" in text
    assert "push: true" in text
