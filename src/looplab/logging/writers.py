"""Append-only log writers (JSONL)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, BinaryIO, TextIO

from looplab.logging.schema import LogEvent


class JSONLWriter:
    """Append-only JSONL writer for LogEvents."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file: TextIO | None = None

    def open(self) -> None:
        self._file = open(self._path, "a", encoding="utf-8")

    def write(self, event: LogEvent) -> None:
        if self._file is None:
            self.open()
        assert self._file is not None
        self._file.write(json.dumps(event.to_dict(), default=_json_default) + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> "JSONLWriter":
        self.open()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "tolist"):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
