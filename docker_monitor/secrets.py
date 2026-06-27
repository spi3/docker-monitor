from __future__ import annotations

from pathlib import Path


def read_secret_file(path: str) -> str:
    value = Path(path).read_text(encoding="utf-8")
    return value[:-1] if value.endswith("\n") else value
