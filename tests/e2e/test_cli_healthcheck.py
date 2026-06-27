from __future__ import annotations

import json
import subprocess
import sys

import pytest


@pytest.mark.e2e
def test_healthcheck_command_returns_ok() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "docker_monitor", "healthcheck"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"status": "ok"}
