from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_config_check_command_validates_config(tmp_path: Path) -> None:
    secret_file = tmp_path / "discord_webhook"
    secret_file.write_text("https://discord.example/webhook\n", encoding="utf-8")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        f"""
host: serenity
receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: {secret_file}
routes:
  - match:
      severity: warning
    receivers:
      - discord-lab
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "docker_health_alerts",
            "config-check",
            "--config",
            str(config_file),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "status": "ok",
        "receivers": 1,
        "routes": 1,
    }
