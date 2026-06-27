from __future__ import annotations

import json

import pytest

from docker_monitor.cli import main


def test_healthcheck_prints_ok(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["healthcheck"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok"}


def test_run_command_reports_not_implemented(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["run"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert json.loads(captured.out)["event"] == "service.startup_failed"
