"""Run package summary: component versions, action/window counts, replay status, benchmark readiness, warnings, config hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _get_component_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in ("looplab", "numpy", "pylsl"):
        try:
            from importlib.metadata import version
            out[name] = version(name)
        except Exception:
            out[name] = "unknown"
    return out


def build_run_package_summary(
    event_counts: dict[str, int],
    benchmark_summary: dict[str, Any],
    run_dir: Path | None = None,
    session_summary: dict[str, Any] | None = None,
    replay_result: dict[str, Any] | None = None,
    config_snapshot: dict[str, Any] | None = None,
    backend: str | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build the run package summary dict. If run_dir is set, load session_summary, replay_result,
    benchmark_summary, config_snapshot from run_dir when not provided.
    """
    if run_dir is not None and run_dir.is_dir():
        if session_summary is None:
            p = run_dir / "session_summary.json"
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    session_summary = json.load(f)
        if replay_result is None:
            p = run_dir / "replay_result.json"
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    replay_result = json.load(f)
        if benchmark_summary is None:
            p = run_dir / "benchmark_summary.json"
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    benchmark_summary = json.load(f)
        if config_snapshot is None:
            p = run_dir / "config_snapshot.json"
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    config_snapshot = json.load(f)

    session_summary = session_summary or {}
    benchmark_summary = benchmark_summary or {}
    replay_result = replay_result
    config_snapshot = config_snapshot or {}

    by_label = benchmark_summary.get("by_label", {})
    window_ready = by_label.get("window_ready", [])
    policy_done = by_label.get("policy_done", [])
    window_count = len(window_ready) if window_ready else len(policy_done)

    if replay_result is not None:
        replay_match_status = {
            "matches": replay_result.get("matches", False),
            "match_count": replay_result.get("match_count", 0),
            "mismatch_count": replay_result.get("mismatch_count", 0),
            "total_logged": replay_result.get("total_logged", 0),
            "total_replayed": replay_result.get("total_replayed", 0),
        }
    else:
        replay_match_status = "no_replay"

    has_e2e = bool(benchmark_summary.get("e2e_latency_seconds"))
    has_ir = bool(benchmark_summary.get("intended_to_realized_seconds"))
    benchmark_readiness: dict[str, Any] = {
        "has_e2e_data": has_e2e,
        "has_intended_to_realized": has_ir,
        "ready": has_e2e or has_ir,
    }
    if benchmark_summary.get("e2e_mean") is not None:
        benchmark_readiness["e2e_mean_seconds"] = benchmark_summary["e2e_mean"]
    if benchmark_summary.get("intended_to_realized_mean") is not None:
        benchmark_readiness["intended_to_realized_mean_seconds"] = benchmark_summary["intended_to_realized_mean"]

    config_hash = ""
    if config_snapshot:
        config_hash = hashlib.sha256(
            json.dumps(config_snapshot, sort_keys=True).encode()
        ).hexdigest()

    backend_val = session_summary.get("backend") or backend or "run"

    summary = {
        "component_versions": _get_component_versions(),
        "action_counts": {
            "control_signal": event_counts.get("control_signal", 0),
            "stimulus_intended": event_counts.get("stimulus_intended", 0),
            "stimulus_realized": event_counts.get("stimulus_realized", 0),
        },
        "window_count": window_count,
        "replay_match_status": replay_match_status,
        "benchmark_readiness": benchmark_readiness,
        "warning_inventory": list(warnings) if warnings else [],
        "config_hash": config_hash,
        "backend": backend_val,
    }
    return summary


def format_run_summary_markdown(summary: dict[str, Any]) -> str:
    """One-page markdown report for RUN_SUMMARY.md."""
    lines = ["# Run package summary", ""]

    lines.append("## Component versions")
    for name, ver in summary.get("component_versions", {}).items():
        lines.append(f"- {name}: {ver}")
    lines.append("")

    ac = summary.get("action_counts", {})
    lines.append("## Action counts")
    lines.append(f"- control_signal: {ac.get('control_signal', 0)}")
    lines.append(f"- stimulus_intended: {ac.get('stimulus_intended', 0)}")
    lines.append(f"- stimulus_realized: {ac.get('stimulus_realized', 0)}")
    lines.append("")

    lines.append(f"## Window count\n{summary.get('window_count', 0)}\n")

    rms = summary.get("replay_match_status", "no_replay")
    lines.append("## Replay match status")
    if isinstance(rms, dict):
        lines.append(f"- matches: {rms.get('matches', False)}")
        lines.append(f"- match_count: {rms.get('match_count', 0)}")
        lines.append(f"- mismatch_count: {rms.get('mismatch_count', 0)}")
        lines.append(f"- total_logged: {rms.get('total_logged', 0)}")
        lines.append(f"- total_replayed: {rms.get('total_replayed', 0)}")
    else:
        lines.append(f"- {rms}")
    lines.append("")

    br = summary.get("benchmark_readiness", {})
    lines.append("## Benchmark readiness")
    lines.append(f"- has_e2e_data: {br.get('has_e2e_data', False)}")
    lines.append(f"- has_intended_to_realized: {br.get('has_intended_to_realized', False)}")
    lines.append(f"- ready: {br.get('ready', False)}")
    if br.get("e2e_mean_seconds") is not None:
        lines.append(f"- e2e_mean_seconds: {br['e2e_mean_seconds']}")
    if br.get("intended_to_realized_mean_seconds") is not None:
        lines.append(f"- intended_to_realized_mean_seconds: {br['intended_to_realized_mean_seconds']}")
    lines.append("")

    warnings = summary.get("warning_inventory", [])
    lines.append("## Warnings")
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append(f"## Config hash\n`{summary.get('config_hash', '')}`\n")
    lines.append(f"## Backend\n{summary.get('backend', 'run')}\n")
    return "\n".join(lines)
