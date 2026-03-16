"""Simple latency report: end-to-end, model, intended->realized."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_latencies(points: list[tuple[str, float]]) -> dict[str, list[float]]:
    """
    points: [(label, lsl_time), ...]. Returns dict of label -> list of timestamps.
    Caller can diff consecutive pull_chunk -> policy_done for e2e latency.
    """
    by_label: dict[str, list[float]] = defaultdict(list)
    for label, t in points:
        by_label[label].append(t)
    return dict(by_label)


def latency_report(
    points: list[tuple[str, float]],
) -> dict[str, Any]:
    """
    Per-run summary: e2e (first pull_chunk to last policy_done in same cycle),
    and intended->realized deltas if both present.
    """
    by_label = compute_latencies(points)
    report: dict[str, Any] = {"by_label": {k: v for k, v in by_label.items()}}

    pull = by_label.get("pull_chunk", [])
    policy = by_label.get("policy_done", [])
    intended = by_label.get("stimulus_intended", [])
    realized = by_label.get("stimulus_realized", [])

    if pull and policy and len(pull) <= len(policy):
        e2e = [policy[i] - pull[i] for i in range(min(len(pull), len(policy)))]
        report["e2e_latency_seconds"] = e2e
        if e2e:
            report["e2e_mean"] = sum(e2e) / len(e2e)
    if intended and realized and len(intended) <= len(realized):
        ir = [realized[i] - intended[i] for i in range(min(len(intended), len(realized)))]
        report["intended_to_realized_seconds"] = ir
        if ir:
            report["intended_to_realized_mean"] = sum(ir) / len(ir)
    return report


def format_report_human(report: dict[str, Any]) -> str:
    """
    Human-readable summary of latency report.
    Returns lines like "E2E latency (chunk→control): mean 0.012 s (N samples)".
    """
    if not report or (not report.get("e2e_latency_seconds") and "intended_to_realized_seconds" not in report):
        return "No benchmark events in log (run with benchmark: true and record benchmark_latency events)."
    lines = []
    if "e2e_latency_seconds" in report:
        e2e = report["e2e_latency_seconds"]
        n = len(e2e)
        mean_s = report.get("e2e_mean")
        if mean_s is not None:
            lines.append(f"E2E latency (chunk→control): mean {mean_s:.4f} s ({n} samples)")
    if "intended_to_realized_seconds" in report:
        ir = report["intended_to_realized_seconds"]
        n = len(ir)
        mean_s = report.get("intended_to_realized_mean")
        if mean_s is not None:
            lines.append(f"Intended→realized: mean {mean_s:.4f} s ({n} samples)")
    return "\n".join(lines) if lines else "No benchmark events in log."


class BenchmarkReport:
    """Build report from BenchmarkHooks points."""

    def __init__(self, hooks: Any = None):
        self._hooks = hooks

    def report(self) -> dict[str, Any]:
        if self._hooks is None:
            return {}
        return latency_report(self._hooks.get_points())
