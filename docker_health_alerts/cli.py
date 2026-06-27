from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from docker_health_alerts import __version__
from docker_health_alerts.config import (
    ConfigError,
    load_config_file,
    load_config_from_env,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docker-health-alerts",
        description="Watch Docker health transitions and route alerts.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="start the monitor service")
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
        print(
            json.dumps(
                {
                    "event": "service.not_implemented",
                    "message": "runtime loop is implemented in a later task",
                },
            ),
            file=sys.stderr,
        )
        return 2

    parser.print_help()
    return 0
