"""Experiment-level types: trial/block context, adaptive params, outcome, experiment state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrialContext:
    """Identifies the current trial for logging and context."""

    trial_index: int
    block_index: int
    condition: str | None = None
    onset_lsl_time: float | None = None
    trial_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_index": self.trial_index,
            "block_index": self.block_index,
            "condition": self.condition,
            "onset_lsl_time": self.onset_lsl_time,
            "trial_id": self.trial_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TrialContext:
        return cls(
            trial_index=int(d.get("trial_index", 0)),
            block_index=int(d.get("block_index", 0)),
            condition=d.get("condition"),
            onset_lsl_time=d.get("onset_lsl_time"),
            trial_id=d.get("trial_id"),
        )


@dataclass
class BlockContext:
    """Identifies the current block."""

    block_index: int
    label: str | None = None
    start_lsl_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_index": self.block_index,
            "label": self.label,
            "start_lsl_time": self.start_lsl_time,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BlockContext:
        return cls(
            block_index=int(d.get("block_index", 0)),
            label=d.get("label"),
            start_lsl_time=d.get("start_lsl_time"),
        )


class AdaptiveParameterState:
    """Mutable dict-like container for adaptive parameters (e.g. difficulty, feedback_type)."""

    def __init__(self, initial: dict[str, Any] | None = None):
        self._params: dict[str, Any] = dict(initial or {})

    def get(self, name: str, default: Any = None) -> Any:
        return self._params.get(name, default)

    def set(self, name: str, value: Any) -> None:
        self._params[name] = value

    def to_dict(self) -> dict[str, Any]:
        return dict(self._params)


@dataclass
class TrialOutcome:
    """Result of a trial as reported by the task."""

    trial_index: int
    block_index: int
    correct: bool | None = None
    rt_sec: float | None = None
    condition: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "trial_index": self.trial_index,
            "block_index": self.block_index,
            "correct": self.correct,
            "rt_sec": self.rt_sec,
            "condition": self.condition,
        }
        if self.extra:
            out["extra"] = self.extra
        return out

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TrialOutcome:
        return cls(
            trial_index=int(d.get("trial_index", 0)),
            block_index=int(d.get("block_index", 0)),
            correct=d.get("correct"),
            rt_sec=d.get("rt_sec"),
            condition=d.get("condition"),
            extra=d.get("extra", {}),
        )


class ExperimentState:
    """Single holder for current experiment position and adaptive state."""

    def __init__(self) -> None:
        self.current_trial: TrialContext | None = None
        self.current_block: BlockContext | None = None
        self.adaptive_params = AdaptiveParameterState()
        self._outcomes: list[TrialOutcome] = []

    def start_block(self, block_index: int, label: str | None = None, lsl_time: float | None = None) -> BlockContext:
        self.current_block = BlockContext(block_index=block_index, label=label, start_lsl_time=lsl_time)
        return self.current_block

    def start_trial(
        self,
        trial_index: int,
        block_index: int,
        condition: str | None = None,
        lsl_time: float | None = None,
        trial_id: str | None = None,
    ) -> TrialContext:
        self.current_trial = TrialContext(
            trial_index=trial_index,
            block_index=block_index,
            condition=condition,
            onset_lsl_time=lsl_time,
            trial_id=trial_id,
        )
        return self.current_trial

    def record_outcome(self, outcome: TrialOutcome) -> None:
        self._outcomes.append(outcome)

    def get_outcomes(self) -> list[TrialOutcome]:
        return list(self._outcomes)
