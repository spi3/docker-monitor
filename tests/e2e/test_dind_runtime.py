from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.docker]

RUN_DIND_ENV = "DOCKER_MONITOR_RUN_DIND_E2E"
DIND_IMAGE = os.environ.get("DOCKER_MONITOR_DIND_IMAGE", "docker:27-dind")


def test_monitor_container_observes_inner_docker_health_transitions(
    tmp_path: Path,
) -> None:
    require_dind_e2e_enabled()
    run(["docker", "info"], timeout=15)

    run_id = uuid.uuid4().hex[:12]
    monitor_image = f"docker-monitor:e2e-{run_id}"
    dind_name = f"docker-monitor-e2e-dind-{run_id}"

    build_monitor_image(monitor_image)

    try:
        start_dind(dind_name)
        wait_for_inner_docker(dind_name)
        load_image_into_dind(dind_name, monitor_image, tmp_path)
        copy_test_files_into_dind(dind_name, tmp_path)

        startup_unhealthy = "e2e-startup-unhealthy"
        flappy = "e2e-flappy"
        monitor = "docker-monitor-e2e"

        start_health_container(
            dind_name,
            image=monitor_image,
            name=startup_unhealthy,
            command="sleep 300",
        )
        wait_for_inner_health(dind_name, startup_unhealthy, "unhealthy")

        start_health_container(
            dind_name,
            image=monitor_image,
            name=flappy,
            command="touch /tmp/healthy && sleep 300",
        )
        wait_for_inner_health(dind_name, flappy, "healthy")

        start_monitor_container(dind_name, image=monitor_image, name=monitor)
        wait_for_mock_alert(
            dind_name,
            monitor,
            container=startup_unhealthy,
            status="firing",
        )

        inner_docker(dind_name, "exec", flappy, "rm", "-f", "/tmp/healthy")
        wait_for_inner_health(dind_name, flappy, "unhealthy")
        wait_for_mock_alert(
            dind_name,
            monitor,
            container=flappy,
            status="firing",
        )

        inner_docker(dind_name, "exec", flappy, "touch", "/tmp/healthy")
        wait_for_inner_health(dind_name, flappy, "healthy")
        wait_for_mock_alert(
            dind_name,
            monitor,
            container=flappy,
            status="resolved",
        )
    finally:
        run(["docker", "rm", "-f", dind_name], check=False, timeout=30)
        run(["docker", "rmi", "-f", monitor_image], check=False, timeout=30)


def require_dind_e2e_enabled() -> None:
    if os.environ.get(RUN_DIND_ENV) != "1":
        pytest.skip(f"set {RUN_DIND_ENV}=1 to run Docker-in-Docker e2e tests")
    if shutil.which("docker") is None:
        pytest.fail("Docker CLI is required for Docker-in-Docker e2e tests")


def build_monitor_image(image: str) -> None:
    run(["docker", "build", "--target", "runtime", "-t", image, "."], timeout=240)


def start_dind(name: str) -> None:
    run(
        [
            "docker",
            "run",
            "-d",
            "--privileged",
            "--name",
            name,
            "-e",
            "DOCKER_TLS_CERTDIR=",
            DIND_IMAGE,
        ],
        timeout=120,
    )


def wait_for_inner_docker(dind_name: str) -> None:
    deadline = time.monotonic() + 90
    last_error = ""
    while time.monotonic() < deadline:
        result = inner_docker(dind_name, "info", check=False, timeout=10)
        if result.returncode == 0:
            return
        last_error = output_text(result)
        time.sleep(1)
    raise AssertionError(f"inner Docker daemon did not become ready:\n{last_error}")


def load_image_into_dind(dind_name: str, image: str, tmp_path: Path) -> None:
    image_tar = tmp_path / "docker-monitor-image.tar"
    with image_tar.open("wb") as output:
        result = subprocess.run(
            ["docker", "save", image],
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))

    stream_file_into_dind(dind_name, image_tar, f"/tmp/{image_tar.name}")
    inner_docker(dind_name, "load", "-i", f"/tmp/{image_tar.name}", timeout=120)


def copy_test_files_into_dind(dind_name: str, tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
host: dind-e2e
monitor:
  mode: label_opt_in
  label: docker-monitor.enable
  send_resolved: true
  send_starting: false
  health_log_output_limit: 200
receivers:
  - name: e2e-drop
    plugin: e2e_plugins.drop_receiver
routes:
  - match:
      severity: warning
    receivers:
      - e2e-drop
""",
        encoding="utf-8",
    )

    plugin_dir = Path(__file__).parent / "plugins" / "e2e_plugins"
    run(["docker", "exec", dind_name, "mkdir", "-p", "/tmp/docker-monitor-e2e/plugins"])
    stream_file_into_dind(
        dind_name,
        config_file,
        "/tmp/docker-monitor-e2e/config.yaml",
    )
    run(
        [
            "docker",
            "exec",
            dind_name,
            "mkdir",
            "-p",
            "/tmp/docker-monitor-e2e/plugins/e2e_plugins",
        ],
    )
    for plugin_file in sorted(plugin_dir.glob("*.py")):
        stream_file_into_dind(
            dind_name,
            plugin_file,
            f"/tmp/docker-monitor-e2e/plugins/e2e_plugins/{plugin_file.name}",
        )


def start_health_container(
    dind_name: str,
    *,
    image: str,
    name: str,
    command: str,
) -> None:
    inner_docker(
        dind_name,
        "run",
        "-d",
        "--name",
        name,
        "--label",
        "docker-monitor.enable=true",
        "--health-cmd",
        "test -f /tmp/healthy",
        "--health-interval",
        "1s",
        "--health-timeout",
        "1s",
        "--health-retries",
        "1",
        "--entrypoint",
        "sh",
        image,
        "-c",
        command,
    )


def start_monitor_container(dind_name: str, *, image: str, name: str) -> None:
    docker_socket_gid = inner_socket_gid(dind_name)
    inner_docker(
        dind_name,
        "run",
        "-d",
        "--name",
        name,
        "--group-add",
        docker_socket_gid,
        "-e",
        "PYTHONPATH=/plugins",
        "-v",
        "/var/run/docker.sock:/var/run/docker.sock:ro",
        "-v",
        "/tmp/docker-monitor-e2e/config.yaml:/config/config.yaml:ro",
        "-v",
        "/tmp/docker-monitor-e2e/plugins:/plugins:ro",
        image,
    )


def inner_socket_gid(dind_name: str) -> str:
    result = run(
        ["docker", "exec", dind_name, "stat", "-c", "%g", "/var/run/docker.sock"],
    )
    return result.stdout.decode("utf-8", errors="replace").strip()


def wait_for_inner_health(
    dind_name: str,
    container_name: str,
    expected: str,
) -> None:
    deadline = time.monotonic() + 60
    last_health = ""
    while time.monotonic() < deadline:
        result = inner_docker(
            dind_name,
            "inspect",
            "-f",
            "{{.State.Health.Status}}",
            container_name,
            check=False,
            timeout=10,
        )
        last_health = result.stdout.decode("utf-8", errors="replace").strip()
        if result.returncode == 0 and last_health == expected:
            return
        time.sleep(1)
    raise AssertionError(
        f"{container_name} health was {last_health!r}, expected {expected!r}"
    )


def wait_for_mock_alert(
    dind_name: str,
    monitor_name: str,
    *,
    container: str,
    status: str,
) -> None:
    deadline = time.monotonic() + 60
    logs = ""
    while time.monotonic() < deadline:
        logs = inner_logs(dind_name, monitor_name)
        for record in parse_json_lines(logs):
            if (
                record.get("event") == "mock_receiver.alert_received"
                and record.get("container") == container
                and record.get("status") == status
            ):
                return
        assert_monitor_running(dind_name, monitor_name, logs)
        time.sleep(1)
    raise AssertionError(
        f"missing mock receiver alert for {container} status {status}\n{logs}"
    )


def assert_monitor_running(dind_name: str, monitor_name: str, logs: str) -> None:
    result = inner_docker(
        dind_name,
        "inspect",
        "-f",
        "{{.State.Running}}",
        monitor_name,
        check=False,
    )
    running = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode == 0 and running == "true":
        return
    raise AssertionError(f"monitor container exited before expected alert\n{logs}")


def parse_json_lines(logs: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in logs.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def inner_logs(dind_name: str, container_name: str) -> str:
    result = inner_docker(dind_name, "logs", container_name, check=False)
    return output_text(result)


def inner_docker(
    dind_name: str,
    *args: str,
    check: bool = True,
    timeout: float = 30,
) -> subprocess.CompletedProcess[bytes]:
    return run(
        ["docker", "exec", dind_name, "docker", *args], check=check, timeout=timeout
    )


def stream_file_into_dind(dind_name: str, source: Path, destination: str) -> None:
    with source.open("rb") as source_file:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                dind_name,
                "sh",
                "-c",
                'cat > "$1"',
                "sh",
                destination,
            ],
            stdin=source_file,
            capture_output=True,
            check=False,
            timeout=120,
        )
    if result.returncode != 0:
        raise AssertionError(
            f"failed to copy {source} into DinD container at {destination}\n"
            f"{output_text(result)}"
        )


def run(
    args: list[str],
    *,
    check: bool = True,
    timeout: float = 30,
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        args,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed with exit {result.returncode}: {args!r}\n"
            f"{output_text(result)}"
        )
    return result


def output_text(result: subprocess.CompletedProcess[bytes]) -> str:
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    return stdout + stderr
