"""Ensure subprocess-based CLI tests see the package (src layout + editable install)."""

from __future__ import annotations

import os
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = str(_REPO / "src")
_existing = os.environ.get("PYTHONPATH", "")
if _existing:
    os.environ["PYTHONPATH"] = _SRC + os.pathsep + _existing
else:
    os.environ["PYTHONPATH"] = _SRC
