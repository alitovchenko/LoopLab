"""Shared exceptions for LoopLab."""

from __future__ import annotations


class UnknownComponentError(Exception):
    """Raised when a plugin name is not in the registry (feature extractor, model, or policy)."""

    def __init__(self, component_type: str, name: str, available: list[str]) -> None:
        self.component_type = component_type
        self.name = name
        self.available = available
        super().__init__(self._message())

    def _message(self) -> str:
        available_str = ", ".join(repr(s) for s in sorted(self.available))
        return (
            f"Unknown {self.component_type} {self.name!r}. "
            f"Registered: [{available_str}]. "
            "Try: python -m looplab list-components   "
            "or: python -m looplab validate-config --config <path> [--plugin plugins.py]"
        )
