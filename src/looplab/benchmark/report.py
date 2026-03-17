"""Simple latency report: end-to-end, per-stage, intended->realized, jitter/variance."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _stats(values: list[float]) -> dict[str, float]:
    """Mean, std, p50, p95 for a list of latencies (seconds)."""
    if not values:
        return {}
    n = len(values)
    sorted_v = sorted(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n if n > 0 else 0.0
    std = variance ** 0.5
    p50 = sorted_v[n // 2] if n else 0.0
    p95 = sorted_v[int(n * 0.95)] if n > 0 and n * 0.95 < n else sorted_v[-1] if sorted_v else 0.0
    return {"mean": mean, "std": std, "p50": p50, "p95": p95}


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
    Per-run summary: e2e, per-stage latencies (acquisition-to-window, preprocess, features,
    model, policy, task_dispatch), intended->realized; plus mean, std, p50, p95 for each.
    Backward compatible: e2e_latency_seconds, e2e_mean, intended_to_realized_seconds, etc.
    """
    by_label = compute_latencies(points)
    report: dict[str, Any] = {"by_label": {k: v for k, v in by_label.items()}}

    pull = by_label.get("pull_chunk", [])
    policy = by_label.get("policy_done", [])
    intended = by_label.get("stimulus_intended", [])
    realized = by_label.get("stimulus_realized", [])

    # E2E (backward compatible)
    if pull and policy and len(pull) <= len(policy):
        e2e = [policy[i] - pull[i] for i in range(min(len(pull), len(policy)))]
        report["e2e_latency_seconds"] = e2e
        if e2e:
            report["e2e_mean"] = sum(e2e) / len(e2e)
            report["e2e_stats"] = _stats(e2e)
    if intended and realized and len(intended) <= len(realized):
        ir = [realized[i] - intended[i] for i in range(min(len(intended), len(realized)))]
        report["intended_to_realized_seconds"] = ir
        if ir:
            report["intended_to_realized_mean"] = sum(ir) / len(ir)
            report["intended_to_realized_stats"] = _stats(ir)

    # Per-stage latencies (align by index; all stage lists should match length of window_ready)
    window_ready = by_label.get("window_ready", [])
    acquisition = by_label.get("acquisition", [])
    preprocess = by_label.get("preprocess_done", [])
    features = by_label.get("features_done", [])
    model = by_label.get("model_done", [])
    policy_done = by_label.get("policy_done", [])
    task_dispatch = by_label.get("task_dispatch", [])

    n = len(window_ready)
    if n:
        if len(acquisition) >= n:
            acq_to_window = [window_ready[i] - acquisition[i] for i in range(n)]
            report["acquisition_to_window_seconds"] = acq_to_window
            report["acquisition_to_window_stats"] = _stats(acq_to_window)
        if len(preprocess) >= n:
            preprocess_lat = [preprocess[i] - window_ready[i] for i in range(n)]
            report["preprocess_latency_seconds"] = preprocess_lat
            report["preprocess_latency_stats"] = _stats(preprocess_lat)
        if len(features) >= n:
            features_lat = [features[i] - preprocess[i] for i in range(n)]
            report["features_latency_seconds"] = features_lat
            report["features_latency_stats"] = _stats(features_lat)
        if len(model) >= n:
            model_lat = [model[i] - features[i] for i in range(n)]
            report["model_latency_seconds"] = model_lat
            report["model_latency_stats"] = _stats(model_lat)
        if len(policy_done) >= n:
            policy_lat = [policy_done[i] - model[i] for i in range(n)]
            report["policy_latency_seconds"] = policy_lat
            report["policy_latency_stats"] = _stats(policy_lat)
        if len(task_dispatch) >= n:
            dispatch_lat = [task_dispatch[i] - policy_done[i] for i in range(n)]
            report["task_dispatch_latency_seconds"] = dispatch_lat
            report["task_dispatch_latency_stats"] = _stats(dispatch_lat)

    return report


def format_report_human(report: dict[str, Any]) -> str:
    """
    Human-readable summary of latency report.
    Includes e2e, intended→realized, and per-stage latencies with mean/std/p95 when present.
    """
    if not report or (not report.get("e2e_latency_seconds") and "intended_to_realized_seconds" not in report
                      and not report.get("preprocess_latency_seconds")):
        return "No benchmark events in log (run with benchmark: true and record benchmark_latency events)."
    lines = []
    if "e2e_latency_seconds" in report:
        e2e = report["e2e_latency_seconds"]
        n = len(e2e)
        mean_s = report.get("e2e_mean")
        if mean_s is not None:
            lines.append(f"E2E latency (chunk→control): mean {mean_s:.4f} s ({n} samples)")
        if "e2e_stats" in report:
            s = report["e2e_stats"]
            lines.append(f"  std={s.get('std', 0):.4f} s, p95={s.get('p95', 0):.4f} s")
    if "intended_to_realized_seconds" in report:
        ir = report["intended_to_realized_seconds"]
        n = len(ir)
        mean_s = report.get("intended_to_realized_mean")
        if mean_s is not None:
            lines.append(f"Intended→realized: mean {mean_s:.4f} s ({n} samples)")
        if "intended_to_realized_stats" in report:
            s = report["intended_to_realized_stats"]
            lines.append(f"  std={s.get('std', 0):.4f} s, p95={s.get('p95', 0):.4f} s")
    for stage_key, label in [
        ("acquisition_to_window_stats", "Acquisition→window"),
        ("preprocess_latency_stats", "Preprocess"),
        ("features_latency_stats", "Features"),
        ("model_latency_stats", "Model"),
        ("policy_latency_stats", "Policy"),
        ("task_dispatch_latency_stats", "Task dispatch"),
    ]:
        if stage_key in report and report[stage_key]:
            s = report[stage_key]
            lines.append(f"{label}: mean={s.get('mean', 0):.4f} s, std={s.get('std', 0):.4f} s, p95={s.get('p95', 0):.4f} s")
    return "\n".join(lines) if lines else "No benchmark events in log."


class BenchmarkReport:
    """Build report from BenchmarkHooks points."""

    def __init__(self, hooks: Any = None):
        self._hooks = hooks

    def report(self) -> dict[str, Any]:
        if self._hooks is None:
            return {}
        return latency_report(self._hooks.get_points())
