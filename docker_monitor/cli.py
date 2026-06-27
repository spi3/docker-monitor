from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from docker_monitor import __version__
from docker_monitor.config import (
    ConfigError,
    load_config_file,
    load_config_from_env,
)
from docker_monitor.runtime import build_runtime_from_config
from docker_monitor.structured_logging import JsonLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docker-monitor",
        description="Watch Docker health transitions and route alerts.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    run = subparsers.add_parser("run", help="start the monitor service")
    run.add_argument("--config", help="config file path")
    subparsers.add_parser("healthcheck", help="check service health")
    config_check = subparsers.add_parser("config-check", help="validate configuration")
    config_check.add_argument("--config", help="config file path")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "healthcheck":
        print(json.dumps({"status": "ok"}))
        return 0

    if args.command == "config-check":
        try:
            config = (
                load_config_file(args.config)
                if args.config is not None
                else load_config_from_env()
            )
        except ConfigError as exc:
            print(
                json.dumps({"event": "config.invalid", "error": str(exc)}),
                file=sys.stderr,
            )
            return 1
        print(
            json.dumps(
                {
                    "status": "ok",
                    "receivers": len(config.receivers),
                    "routes": len(config.routes),
                },
            ),
        )
        return 0

    if args.command == "run":
        logger = JsonLogger()
        try:
            config = (
                load_config_file(args.config)
                if args.config is not None
                else load_config_from_env()
            )
            runtime = build_runtime_from_config(config, logger=logger)
            runtime.install_signal_handlers()
            return runtime.run()
        except (ConfigError, ValueError, RuntimeError) as exc:
            logger.error("service.startup_failed", error=exc.__class__.__name__)
            return 1

    parser.print_help()
    return 0
