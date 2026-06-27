from __future__ import annotations

from pathlib import Path

import pytest

from docker_monitor.config import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_MONITOR_LABEL,
    ConfigError,
    load_config_file,
    load_config_from_env,
    parse_duration,
)


def write_config(tmp_path: Path, content: str) -> Path:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


def test_empty_config_uses_documented_defaults(tmp_path: Path) -> None:
    config = load_config_file(write_config(tmp_path, "{}"))

    assert config.host
    assert config.severity == "warning"
    assert config.monitor.mode == "label_opt_in"
    assert config.monitor.label == DEFAULT_MONITOR_LABEL
    assert config.monitor.send_resolved is True
    assert config.monitor.send_starting is False
    assert config.monitor.health_log_output_limit == 1000
    assert config.receivers == []
    assert config.routes == []


def test_load_config_from_env_uses_config_file_override(tmp_path: Path) -> None:
    config_file = write_config(tmp_path, "host: serenity\n")

    config = load_config_from_env({"CONFIG_FILE": str(config_file)})

    assert config.host == "serenity"


def test_load_config_from_env_uses_default_path_when_unset() -> None:
    with pytest.raises(ConfigError, match=DEFAULT_CONFIG_FILE):
        load_config_from_env({})


def test_receiver_and_route_validation_with_secret_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "webhook_url"
    secret_file.write_text("https://example.invalid/webhook\n", encoding="utf-8")
    header_file = tmp_path / "authorization"
    header_file.write_text("Bearer secret\n", encoding="utf-8")

    config = load_config_file(
        write_config(
            tmp_path,
            f"""
host: serenity
monitor:
  mode: label_opt_out
receivers:
  - name: raw-webhook
    plugin: generic-webhook
    config:
      url_file: {secret_file}
      timeout: 500ms
      header_files:
        Authorization: {header_file}
routes:
  - match:
      severity: warning
    receivers:
      - raw-webhook
""",
        ),
    )

    receiver = config.receivers[0]
    assert config.monitor.mode == "label_opt_out"
    assert receiver.name == "raw-webhook"
    assert receiver.config["timeout"] == 0.5
    assert config.routes[0].receivers == ["raw-webhook"]


@pytest.mark.parametrize("value, expected", [("10s", 10.0), ("2m", 120.0), (3, 3.0)])
def test_parse_duration(value: str | int, expected: float) -> None:
    assert parse_duration(value) == expected


@pytest.mark.parametrize("value", ["", "abc", "10d", 0, -1, True])
def test_parse_duration_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        if isinstance(value, str | int | float):
            parse_duration(value)
        else:
            raise ValueError


def test_invalid_monitor_mode_fails(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path,
        """
monitor:
  mode: everything
""",
    )

    with pytest.raises(ConfigError, match="mode"):
        load_config_file(config_file)


def test_duplicate_receiver_names_fail(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path,
        """
receivers:
  - name: duplicate
    plugin: discord
  - name: duplicate
    plugin: generic-webhook
""",
    )

    with pytest.raises(ConfigError, match="duplicate receiver names"):
        load_config_file(config_file)


def test_unknown_plugin_fails(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path,
        """
receivers:
  - name: slack-lab
    plugin: slack
""",
    )

    with pytest.raises(ConfigError, match="unknown plugin 'slack'"):
        load_config_file(config_file)


def test_unknown_route_receiver_fails(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path,
        """
routes:
  - match:
      severity: warning
    receivers:
      - missing
""",
    )

    with pytest.raises(ConfigError, match="routes reference unknown receivers"):
        load_config_file(config_file)


def test_missing_secret_file_fails_without_secret_value(tmp_path: Path) -> None:
    missing_secret = tmp_path / "missing_secret"
    config_file = write_config(
        tmp_path,
        f"""
receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: {missing_secret}
""",
    )

    with pytest.raises(ConfigError, match="webhook_url_file is not readable"):
        load_config_file(config_file)


def test_inline_and_file_secret_pair_fails(tmp_path: Path) -> None:
    secret_file = tmp_path / "webhook_url"
    secret_file.write_text("https://example.invalid/webhook\n", encoding="utf-8")
    config_file = write_config(
        tmp_path,
        f"""
receivers:
  - name: raw-webhook
    plugin: generic-webhook
    config:
      url: https://example.invalid/inline
      url_file: {secret_file}
""",
    )

    with pytest.raises(ConfigError, match="either 'url' or 'url_file'"):
        load_config_file(config_file)
