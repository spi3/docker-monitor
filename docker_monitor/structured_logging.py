from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any, Literal, TextIO

LogLevel = Literal["debug", "info", "warning", "error"]


class JsonLogger:
    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout

    def log(self, level: LogLevel, event: str, **fields: Any) -> None:
        record = {
            "time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": level,
            "event": event,
            **fields,
        }
        print(json.dumps(record, sort_keys=True), file=self._stream, flush=True)

    def debug(self, event: str, **fields: Any) -> None:
        self.log("debug", event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self.log("info", event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self.log("warning", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log("error", event, **fields)
