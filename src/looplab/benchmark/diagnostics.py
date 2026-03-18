"""Run-quality diagnostics: structured findings (info/warning/critical), health rollup."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class DiagnosticLevel:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RunDiagnosticsConfig:
    """Thresholds for diagnostic checks. Override per-field for tuning."""

    e2e_p95_warning_sec: float = 0.12
    e2e_p95_critical_sec: float = 0.35
    e2e_std_warning_sec: float = 0.04
    e2e_std_critical_sec: float = 0.12
    stage_p95_warning_sec: float = 0.08
    stage_p95_critical_sec: float = 0.25
    ack_p95_warning_sec: float = 0.15
    ack_p95_critical_sec: float = 0.5
    realized_missing_ratio_warning: float = 0.08
    realized_missing_ratio_critical: float = 0.25
    replay_mismatch_warning_count: int = 1
    replay_mismatch_critical_ratio: float = 0.15
    min_expected_chunk_interval_sec: float = 0.015
    min_stream_chunk_ratio_warning: float = 0.4
    burst_window_sec: float = 0.1
    burst_count_warning: int = 6
    burst_count_critical: int = 15
    low_confidence_fraction_warning: float = 0.45
    low_confidence_fraction_critical: float = 0.8
    confidence_high_threshold: float = 0.999
    invalid_nan_ratio_warning: float = 0.01
    invalid_nan_ratio_critical: float = 0.08
    stream_scan_max_lines: int = 50_000
    adaptation_min_control_signals: int = 40
    min_model_outputs_for_confidence_check: int = 10


def _finding(
    level: str,
    code: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {"level": level, "code": code, "message": message, "detail": detail or {}}


def _chunk_has_nan(data: Any) -> bool:
    if data is None:
        return True
    if isinstance(data, list):
        for row in data:
            if isinstance(row, list):
                for x in row:
                    if x is None:
                        return True
                    if isinstance(x, float) and math.isnan(x):
                        return True
            elif row is None:
                return True
    return False


def _scan_stream_invalid_ratio(stream_path: Path | None, max_lines: int) -> tuple[int, int, float]:
    """Returns (nan_chunks, total_chunks_scanned, ratio)."""
    if stream_path is None or not stream_path.exists():
        return 0, 0, 0.0
    nan_c = 0
    total = 0
    try:
        with open(stream_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total += 1
                if _chunk_has_nan(d.get("data")):
                    nan_c += 1
    except OSError:
        return 0, 0, 0.0
    ratio = nan_c / total if total else 0.0
    return nan_c, total, ratio


def _parse_log_extras(log_path: Path | None) -> tuple[list[float], list[float | None], int]:
    """control_signal times, model confidences (None if missing), lines read."""
    ctrl_times: list[float] = []
    confidences: list[float | None] = []
    n = 0
    if log_path is None or not log_path.exists():
        return ctrl_times, confidences, 0
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            et = d.get("event_type", "")
            if et == "control_signal":
                ctrl_times.append(float(d.get("lsl_time", 0)))
            elif et == "model_output":
                p = d.get("payload") or {}
                c = p.get("confidence")
                confidences.append(float(c) if c is not None else None)
    return ctrl_times, confidences, n


def _max_burst_count(times: list[float], window: float) -> int:
    if not times or window <= 0:
        return 0
    t_sorted = sorted(times)
    best = 0
    j = 0
    for i, t in enumerate(t_sorted):
        while j < len(t_sorted) and t_sorted[j] - t <= window:
            j += 1
        best = max(best, j - i)
    return best


def _worst_stage_p95(bench: dict[str, Any]) -> tuple[str | None, float | None]:
    best_p95 = 0.0
    best_key = None
    for key, label in [
        ("preprocess_latency_stats", "preprocess"),
        ("features_latency_stats", "features"),
        ("model_latency_stats", "model"),
        ("policy_latency_stats", "policy"),
        ("task_dispatch_latency_stats", "task_dispatch"),
    ]:
        s = bench.get(key)
        if isinstance(s, dict) and s.get("p95") is not None:
            p95 = float(s["p95"])
            if p95 > best_p95:
                best_p95 = p95
                best_key = label
    return best_key, best_p95 if best_key else None


def build_run_diagnostics(
    event_counts: dict[str, int],
    benchmark_summary: dict[str, Any],
    replay_result: dict[str, Any] | None,
    log_path: Path | str | None,
    stream_path: Path | str | None,
    session_summary: dict[str, Any],
    cfg: RunDiagnosticsConfig | None = None,
) -> dict[str, Any]:
    """
    Produce diagnostics dict: health, findings, checks, threshold_snapshot.
    health: healthy | degraded | unhealthy (any critical -> unhealthy; warning only -> degraded).
    """
    c = cfg or RunDiagnosticsConfig()
    findings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    degraded_run = bool(session_summary.get("degraded"))
    duration = float(session_summary.get("duration_sec") or 0.0)

    def add_f(level: str, code: str, msg: str, detail: dict | None = None) -> None:
        if degraded_run and level == DiagnosticLevel.CRITICAL:
            level = DiagnosticLevel.WARNING
        elif degraded_run and level == DiagnosticLevel.WARNING and code in (
            "replay_mismatch",
            "missing_realized_events",
            "invalid_stream_windows",
            "insufficient_stream_volume",
        ):
            level = DiagnosticLevel.INFO
        findings.append(_finding(level, code, msg, detail))

    log_p = Path(log_path) if log_path else None
    stream_p = Path(stream_path) if stream_path else None

    # --- Benchmark: e2e latency / jitter ---
    e2e_stats = benchmark_summary.get("e2e_stats") or {}
    e2e_p95 = e2e_stats.get("p95")
    e2e_std = e2e_stats.get("std")
    checks.append({"name": "e2e_latency", "p95_sec": e2e_p95, "std_sec": e2e_std})
    if e2e_p95 is not None:
        if e2e_p95 >= c.e2e_p95_critical_sec:
            add_f(DiagnosticLevel.CRITICAL, "e2e_latency_high", f"E2E p95 latency very high ({e2e_p95:.4f}s)", {"p95": e2e_p95})
        elif e2e_p95 >= c.e2e_p95_warning_sec:
            add_f(DiagnosticLevel.WARNING, "e2e_latency_elevated", f"E2E p95 latency elevated ({e2e_p95:.4f}s)", {"p95": e2e_p95})
    if e2e_std is not None and e2e_stats.get("mean"):
        mean = float(e2e_stats["mean"])
        if mean > 1e-6 and e2e_std >= c.e2e_std_warning_sec:
            if e2e_std >= c.e2e_std_critical_sec:
                add_f(DiagnosticLevel.WARNING, "e2e_jitter_high", f"High E2E jitter (std={e2e_std:.4f}s)", {"std": e2e_std, "mean": mean})
            elif e2e_std / mean > 0.35:
                add_f(DiagnosticLevel.INFO, "e2e_jitter_elevated", f"Elevated E2E timing variability (std={e2e_std:.4f}s)", {"std": e2e_std})

    # --- Per-stage p95 ---
    stage_name, stage_p95 = _worst_stage_p95(benchmark_summary)
    checks.append({"name": "worst_stage_latency", "stage": stage_name, "p95_sec": stage_p95})
    if stage_p95 is not None:
        if stage_p95 >= c.stage_p95_critical_sec:
            add_f(DiagnosticLevel.WARNING, "stage_latency_high", f"Stage '{stage_name}' p95 high ({stage_p95:.4f}s)", {"stage": stage_name, "p95": stage_p95})
        elif stage_p95 >= c.stage_p95_warning_sec:
            add_f(DiagnosticLevel.INFO, "stage_latency_elevated", f"Stage '{stage_name}' p95 elevated ({stage_p95:.4f}s)", {"stage": stage_name, "p95": stage_p95})

    # --- Ack delay (intended -> realized) ---
    ir_stats = benchmark_summary.get("intended_to_realized_stats") or {}
    ir_p95 = ir_stats.get("p95")
    checks.append({"name": "task_ack_delay", "p95_sec": ir_p95})
    if ir_p95 is not None:
        if ir_p95 >= c.ack_p95_critical_sec:
            add_f(DiagnosticLevel.WARNING, "task_ack_delay_high", f"Task acknowledgment delay p95 high ({ir_p95:.4f}s)", {"p95": ir_p95})
        elif ir_p95 >= c.ack_p95_warning_sec:
            add_f(DiagnosticLevel.INFO, "task_ack_delay_elevated", f"Task acknowledgment delay p95 elevated ({ir_p95:.4f}s)", {"p95": ir_p95})

    # --- Missing realized ---
    intended = event_counts.get("stimulus_intended", 0)
    realized = event_counts.get("stimulus_realized", 0)
    checks.append({"name": "intended_vs_realized", "intended": intended, "realized": realized})
    if intended > 0:
        miss_ratio = 1.0 - (realized / intended)
        if miss_ratio >= c.realized_missing_ratio_critical:
            add_f(DiagnosticLevel.CRITICAL, "missing_realized_events", f"Many missing stimulus_realized ({realized}/{intended})", {"intended": intended, "realized": realized})
        elif miss_ratio >= c.realized_missing_ratio_warning:
            add_f(DiagnosticLevel.WARNING, "missing_realized_events", f"Some stimulus_realized missing ({realized}/{intended})", {"intended": intended, "realized": realized})

    # --- Replay ---
    checks.append({"name": "replay", "replay_result": replay_result is not None})
    tr = int(replay_result.get("total_replayed", 0)) if replay_result else 0
    if replay_result and replay_result.get("total_logged", 0) > 0 and tr > 0:
        mc = int(replay_result.get("mismatch_count", 0))
        tl = int(replay_result.get("total_logged", 1))
        ratio = mc / max(tl, 1)
        if not replay_result.get("matches", False):
            if mc >= max(c.replay_mismatch_critical_ratio * tl, 5) or ratio >= c.replay_mismatch_critical_ratio:
                add_f(DiagnosticLevel.CRITICAL, "replay_mismatch", f"Replay mismatch severe ({mc} mismatches / {tl})", {"mismatch_count": mc, "total_logged": tl})
            elif mc >= c.replay_mismatch_warning_count:
                add_f(DiagnosticLevel.WARNING, "replay_mismatch", f"Replay mismatch ({mc} mismatches / {tl})", {"mismatch_count": mc, "total_logged": tl})

    # --- Stream volume ---
    stream_lines = 0
    if stream_p and stream_p.exists():
        try:
            with open(stream_p, encoding="utf-8") as f:
                for _ in f:
                    stream_lines += 1
        except OSError:
            pass
    expected = 0.0
    if duration > 0 and c.min_expected_chunk_interval_sec > 0:
        expected = duration / c.min_expected_chunk_interval_sec
    checks.append({"name": "stream_volume", "chunks": stream_lines, "expected_approx": expected})
    if expected > 10 and stream_lines > 0:
        ratio = stream_lines / expected
        if ratio < c.min_stream_chunk_ratio_warning:
            add_f(DiagnosticLevel.WARNING, "insufficient_stream_volume", f"Stream chunk count low vs duration ({stream_lines} chunks, ~{expected:.0f} expected)", {"chunks": stream_lines, "expected_approx": expected})

    # --- Invalid windows in stream ---
    nan_c, scanned, nan_ratio = _scan_stream_invalid_ratio(stream_p, c.stream_scan_max_lines)
    checks.append({"name": "invalid_stream_windows", "nan_chunks": nan_c, "scanned": scanned, "ratio": nan_ratio})
    if scanned > 0 and nan_ratio >= c.invalid_nan_ratio_critical:
        add_f(DiagnosticLevel.WARNING, "invalid_stream_windows", f"High fraction of invalid (NaN) stream chunks ({nan_ratio:.2%})", {"ratio": nan_ratio, "count": nan_c})
    elif scanned > 0 and nan_ratio >= c.invalid_nan_ratio_warning:
        add_f(DiagnosticLevel.INFO, "invalid_stream_windows", f"Some invalid (NaN) stream chunks ({nan_ratio:.2%})", {"ratio": nan_ratio, "count": nan_c})

    # --- Log extras: bursts, low confidence, no adaptation ---
    ctrl_times, confidences, _ = _parse_log_extras(log_p)
    burst = _max_burst_count(ctrl_times, c.burst_window_sec)
    checks.append({"name": "control_signal_burst", "max_in_window": burst, "window_sec": c.burst_window_sec})
    if burst >= c.burst_count_critical:
        add_f(DiagnosticLevel.WARNING, "action_burst_suspicious", f"Many control signals in {c.burst_window_sec}s window (max={burst})", {"max_burst": burst})
    elif burst >= c.burst_count_warning:
        add_f(DiagnosticLevel.INFO, "action_burst_elevated", f"Clustered control signals (max {burst} in {c.burst_window_sec}s)", {"max_burst": burst})

    defined_conf = [x for x in confidences if x is not None]
    low_conf = [x for x in defined_conf if x < c.confidence_high_threshold]
    checks.append({"name": "model_confidence", "n_logged": len(defined_conf), "low_confidence_count": len(low_conf)})
    if len(defined_conf) >= c.min_model_outputs_for_confidence_check:
        frac = len(low_conf) / len(defined_conf)
        if frac >= c.low_confidence_fraction_critical:
            add_f(DiagnosticLevel.WARNING, "low_model_confidence_run", f"Model low-confidence for much of run ({frac:.0%} of outputs)", {"fraction": frac})
        elif frac >= c.low_confidence_fraction_warning:
            add_f(DiagnosticLevel.INFO, "low_model_confidence_elevated", f"Elevated low-confidence model outputs ({frac:.0%})", {"fraction": frac})

    n_ctrl = event_counts.get("control_signal", 0)
    n_adapt = event_counts.get("adaptive_params_update", 0)
    has_trial = event_counts.get("trial_start", 0) > 0
    checks.append({"name": "adaptation_events", "control_signals": n_ctrl, "adaptive_params_update": n_adapt})
    if has_trial and n_ctrl >= c.adaptation_min_control_signals and n_adapt == 0:
        add_f(DiagnosticLevel.INFO, "no_adaptation_logged", "No adaptive_params_update events despite many control signals and trial structure", {"control_signals": n_ctrl})

    # --- No benchmark data ---
    if not benchmark_summary.get("e2e_latency_seconds") and not benchmark_summary.get("intended_to_realized_seconds"):
        if event_counts.get("benchmark_latency", 0) == 0:
            add_f(DiagnosticLevel.INFO, "no_benchmark_events", "No benchmark latency events; latency diagnostics limited", {})

    # Health rollup
    has_critical = any(f["level"] == DiagnosticLevel.CRITICAL for f in findings)
    has_warning = any(f["level"] == DiagnosticLevel.WARNING for f in findings)
    if has_critical:
        health = "unhealthy"
    elif has_warning:
        health = "degraded"
    else:
        health = "healthy"

    return {
        "health": health,
        "findings": findings,
        "checks": checks,
        "thresholds": {k: v for k, v in asdict(c).items()},
        "degraded_run_adjusted": degraded_run,
    }


def diagnostics_to_jsonable(d: dict[str, Any]) -> dict[str, Any]:
    """Ensure JSON-serializable (findings already are)."""
    return json.loads(json.dumps(d, default=str))


def write_run_diagnostics_artifacts(
    out_dir: Path,
    event_counts: dict[str, int],
    benchmark_summary: dict[str, Any],
    replay_result: dict[str, Any] | None,
    log_path: Path,
    stream_path: Path,
    session_summary: dict[str, Any],
    run_warnings: list[str],
    cfg: RunDiagnosticsConfig | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """
    Run build_run_diagnostics, write diagnostics.json, merge into session_summary.
    Returns (diagnostics dict, expanded warning_inventory for run_package_summary).
    """
    diag = build_run_diagnostics(
        event_counts,
        benchmark_summary,
        replay_result,
        log_path,
        stream_path,
        session_summary,
        cfg,
    )
    merge_diagnostics_into_session_summary(session_summary, diag, run_warnings)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(diagnostics_to_jsonable(diag), f, indent=2)
    inv = list(run_warnings)
    for item in diag.get("findings", []):
        if item["level"] in (DiagnosticLevel.WARNING, DiagnosticLevel.CRITICAL):
            inv.append(f"{item['level']}: {item['code']} — {item['message']}")
    return diag, inv


def merge_diagnostics_into_session_summary(
    session_summary: dict[str, Any],
    diagnostics: dict[str, Any],
    legacy_warnings: list[str] | None = None,
) -> None:
    """Mutate session_summary with run_health, diagnostics fields, merged warning strings."""
    session_summary["run_health"] = diagnostics.get("health", "healthy")
    findings = diagnostics.get("findings") or []
    session_summary["diagnostics_summary"] = (
        f"{session_summary['run_health']}: {len(findings)} finding(s)"
    )
    session_summary["diagnostic_findings"] = [
        {"level": f["level"], "code": f["code"], "message": f["message"]} for f in findings
    ]
    crit_warn = [f"{f['level']}: {f['message']}" for f in findings if f["level"] in (DiagnosticLevel.WARNING, DiagnosticLevel.CRITICAL)]
    merged = list(legacy_warnings or [])
    merged.extend(crit_warn)
    session_summary["warning_messages"] = merged
