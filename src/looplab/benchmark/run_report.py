"""Methods-ready run report: run_report.json + run_report.md from a run directory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CANONICAL_ARTIFACTS = [
    "config_snapshot.json",
    "components_manifest.json",
    "events.jsonl",
    "stream.jsonl",
    "benchmark_summary.json",
    "replay_result.json",
    "session_summary.json",
    "diagnostics.json",
    "run_package_summary.json",
    "RUN_SUMMARY.md",
    "run_report.json",
    "run_report.md",
]


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _scan_events(log_path: Path) -> tuple[dict[str, int], str | None, list[str] | None]:
    """Event type counts, first control_signal action, keys from last adaptive_params_update payload."""
    counts: dict[str, int] = {}
    first_action: str | None = None
    last_adaptive_keys: list[str] | None = None
    if not log_path.exists():
        return counts, None, None
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                et = d.get("event_type", "")
                counts[et] = counts.get(et, 0) + 1
                if et == "control_signal" and first_action is None:
                    first_action = (d.get("payload") or {}).get("action")
                if et == "adaptive_params_update":
                    p = d.get("payload")
                    if isinstance(p, dict) and p:
                        last_adaptive_keys = sorted(p.keys())
    except OSError:
        pass
    return counts, first_action, last_adaptive_keys


def _window_count(bench: dict[str, Any]) -> int:
    by_label = bench.get("by_label") or {}
    wr = by_label.get("window_ready") or []
    pd = by_label.get("policy_done") or []
    return len(wr) if wr else len(pd)


def _stage_p95_table(bench: dict[str, Any]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for key, label in [
        ("preprocess_latency_stats", "preprocess"),
        ("features_latency_stats", "features"),
        ("model_latency_stats", "model"),
        ("policy_latency_stats", "policy"),
        ("task_dispatch_latency_stats", "task_dispatch"),
    ]:
        s = bench.get(key)
        if isinstance(s, dict) and s.get("p95") is not None:
            out[label] = float(s["p95"])
    return out


def build_run_report(run_dir: Path | str) -> dict[str, Any]:
    """
    Aggregate methods-ready report from artifacts under run_dir.
    Safe to call when some files are missing.
    """
    run_dir = Path(run_dir)
    event_counts, first_control_action, last_adaptive_keys = _scan_events(run_dir / "events.jsonl")
    config = _load_json(run_dir / "config_snapshot.json") or {}
    session = _load_json(run_dir / "session_summary.json") or {}
    bench = _load_json(run_dir / "benchmark_summary.json") or {}
    replay = _load_json(run_dir / "replay_result.json")
    diagnostics = _load_json(run_dir / "diagnostics.json") or {}
    manifest = _load_json(run_dir / "components_manifest.json")

    lsl = config.get("lsl") or {}
    buf = config.get("buffer") or {}
    duration = float(session.get("duration_sec") or 0.0)
    wc = _window_count(bench)
    eff_wps = (wc / duration) if duration > 0 and wc else None

    paradigm = session.get("paradigm")
    policy_name = config.get("policy") or "unknown"
    if paradigm == "psychopy_e2e":
        adaptation_target = "psychopy_e2e: set_value → stimulus radius"
    elif paradigm:
        adaptation_target = str(paradigm)
    elif first_control_action:
        adaptation_target = f"{policy_name} → {first_control_action}"
    else:
        adaptation_target = str(policy_name)

    try:
        from importlib.metadata import version

        looplab_ver = version("looplab")
    except Exception:
        looplab_ver = "unknown"
    if manifest and manifest.get("looplab_version"):
        looplab_ver = manifest["looplab_version"]

    e2e_stats = bench.get("e2e_stats") or {}
    ir_stats = bench.get("intended_to_realized_stats") or {}
    timing_summary: dict[str, Any] = {}
    if e2e_stats:
        timing_summary["e2e_seconds"] = {k: e2e_stats.get(k) for k in ("mean", "std", "p50", "p95") if e2e_stats.get(k) is not None}
    if ir_stats:
        timing_summary["intended_to_realized_seconds"] = {
            k: ir_stats.get(k) for k in ("mean", "std", "p50", "p95") if ir_stats.get(k) is not None
        }

    findings = diagnostics.get("findings") or []
    n_crit = sum(1 for f in findings if f.get("level") == "critical")
    n_warn = sum(1 for f in findings if f.get("level") == "warning")
    n_info = sum(1 for f in findings if f.get("level") == "info")
    health = session.get("run_health") or diagnostics.get("health") or "unknown"

    methods: dict[str, Any] = {
        "window_size_samples": lsl.get("chunk_size"),
        "buffer_max_samples": buf.get("max_samples"),
        "n_channels": buf.get("n_channels"),
        "feature_extractor_name": config.get("feature_extractor"),
        "model_name": config.get("model"),
        "policy_name": policy_name,
        "preprocess": config.get("preprocess"),
        "adaptation_target": adaptation_target,
        "backend": session.get("backend", "unknown"),
        "duration_sec": duration or None,
        "effective_windows_per_sec": eff_wps,
        "timing_summary": timing_summary or None,
        "warning_status": {
            "run_health": health,
            "diagnostic_critical": n_crit,
            "diagnostic_warning": n_warn,
            "diagnostic_info": n_info,
        },
        "looplab_version": looplab_ver,
    }

    experiment_summary = {
        "trial_start": event_counts.get("trial_start", 0),
        "trial_end": event_counts.get("trial_end", 0),
        "block_start": event_counts.get("block_start", 0),
        "block_end": event_counts.get("block_end", 0),
        "trial_outcome": event_counts.get("trial_outcome", 0),
        "has_experiment_events": any(
            event_counts.get(k, 0) > 0
            for k in ("trial_start", "block_start", "trial_outcome")
        ),
    }

    adaptation = {
        "adaptive_params_update": event_counts.get("adaptive_params_update", 0),
        "control_signal": event_counts.get("control_signal", 0),
        "adaptation_target": adaptation_target,
        "first_control_action": first_control_action,
    }

    replay_agreement: dict[str, Any] | None = None
    if replay:
        div = replay.get("divergences") or []
        replay_agreement = {
            "matches": replay.get("matches"),
            "match_count": replay.get("match_count"),
            "mismatch_count": replay.get("mismatch_count"),
            "total_logged": replay.get("total_logged"),
            "total_replayed": replay.get("total_replayed"),
            "divergences_sample": div[:5],
            "divergences_total": len(div),
        }

    benchmark_highlights = {
        "e2e_mean_sec": bench.get("e2e_mean"),
        "e2e_stats": bench.get("e2e_stats"),
        "intended_to_realized_mean_sec": bench.get("intended_to_realized_mean"),
        "intended_to_realized_stats": bench.get("intended_to_realized_stats"),
        "stage_p95_seconds": _stage_p95_table(bench),
        "window_count": wc,
    }

    diagnostics_summary = {
        "health": diagnostics.get("health"),
        "degraded_run_adjusted": diagnostics.get("degraded_run_adjusted"),
        "findings_by_level": {"critical": n_crit, "warning": n_warn, "info": n_info},
        "findings": findings,
    }

    task_level_summary: dict[str, Any] | None = None
    if (
        paradigm == "psychopy_e2e"
        or event_counts.get("trial_outcome", 0) > 0
        or event_counts.get("stimulus_realized", 0) > 0
    ):
        if paradigm == "psychopy_e2e":
            ap_logged = "stimulus_size"
        elif last_adaptive_keys:
            ap_logged = ", ".join(last_adaptive_keys[:12])
        else:
            ap_logged = None
        task_level_summary = {
            "trial_starts": event_counts.get("trial_start", 0),
            "trial_outcomes": event_counts.get("trial_outcome", 0),
            "block_starts": event_counts.get("block_start", 0),
            "stimulus_intended": event_counts.get("stimulus_intended", 0),
            "stimulus_realized": event_counts.get("stimulus_realized", 0),
            "intended_to_realized_mean_sec": bench.get("intended_to_realized_mean"),
        }
        if ap_logged:
            task_level_summary["adaptive_param_logged"] = ap_logged

    config_hash = ""
    if config:
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()

    pipeline: dict[str, Any]
    if manifest:
        pipeline = {
            "source": "components_manifest.json",
            "looplab_version": manifest.get("looplab_version"),
            "feature_extractor": manifest.get("feature_extractor"),
            "model": manifest.get("model"),
            "policy": manifest.get("policy"),
        }
    else:
        pipeline = {
            "source": "config_snapshot.json",
            "feature_extractor": {"name": config.get("feature_extractor"), "config": config.get("feature_extractor_config")},
            "model": {"name": config.get("model"), "config": config.get("model_config")},
            "policy": {"name": config.get("policy"), "config": config.get("policy_config")},
        }

    artifact_inventory = []
    for name in CANONICAL_ARTIFACTS:
        p = run_dir / name
        if p.exists():
            try:
                artifact_inventory.append({"name": name, "present": True, "bytes": p.stat().st_size})
            except OSError:
                artifact_inventory.append({"name": name, "present": True, "bytes": None})
        else:
            artifact_inventory.append({"name": name, "present": False, "bytes": None})

    report: dict[str, Any] = {
        "run_dir": str(run_dir.resolve()),
        "methods": methods,
        "pipeline": pipeline,
        "backend": session.get("backend", "unknown"),
        "config_hash": config_hash,
        "experiment_summary": experiment_summary,
        "adaptation": adaptation,
        "replay_agreement": replay_agreement,
        "benchmark_highlights": benchmark_highlights,
        "diagnostics_summary": diagnostics_summary,
        "artifact_inventory": artifact_inventory,
        "event_counts_selected": {
            k: event_counts.get(k, 0)
            for k in (
                "control_signal",
                "stimulus_intended",
                "stimulus_realized",
                "model_output",
                "benchmark_latency",
            )
        },
    }
    if task_level_summary is not None:
        report["task_level_summary"] = task_level_summary
    return report


def format_run_report_markdown(report: dict[str, Any]) -> str:
    lines = ["# Run report (methods-ready)", ""]

    m = report.get("methods") or {}
    lines.append("## Methods (citable)")
    lines.append(f"- **LoopLab version:** {m.get('looplab_version', 'n/a')}")
    lines.append(f"- **Backend:** {m.get('backend', 'n/a')}")
    lines.append(f"- **Duration (s):** {m.get('duration_sec', 'n/a')}")
    lines.append(f"- **Window size (samples / chunk):** {m.get('window_size_samples', 'n/a')}")
    lines.append(f"- **Buffer max samples:** {m.get('buffer_max_samples', 'n/a')}")
    lines.append(f"- **Channels:** {m.get('n_channels', 'n/a')}")
    lines.append(f"- **Feature extractor:** {m.get('feature_extractor_name', 'n/a')}")
    lines.append(f"- **Model:** {m.get('model_name', 'n/a')}")
    lines.append(f"- **Policy:** {m.get('policy_name', 'n/a')}")
    lines.append(f"- **Preprocess:** {m.get('preprocess', 'n/a')}")
    lines.append(f"- **Adaptation target:** {m.get('adaptation_target', 'n/a')}")
    if m.get("effective_windows_per_sec") is not None:
        lines.append(f"- **Effective windows/s:** {m['effective_windows_per_sec']:.2f}")
    ws = m.get("warning_status") or {}
    lines.append(
        f"- **Warning status:** health={ws.get('run_health', '?')}, "
        f"critical={ws.get('diagnostic_critical', 0)}, warning={ws.get('diagnostic_warning', 0)}, info={ws.get('diagnostic_info', 0)}"
    )
    ts = m.get("timing_summary") or {}
    if ts.get("e2e_seconds"):
        e = ts["e2e_seconds"]
        lines.append(f"- **E2E latency (s):** mean={e.get('mean')}, std={e.get('std')}, p95={e.get('p95')}")
    if ts.get("intended_to_realized_seconds"):
        e = ts["intended_to_realized_seconds"]
        lines.append(f"- **Intended→realized (s):** mean={e.get('mean')}, std={e.get('std')}, p95={e.get('p95')}")
    lines.append("")

    lines.append("## Pipeline (resolved)")
    lines.append("```json")
    lines.append(json.dumps(report.get("pipeline"), indent=2))
    lines.append("```")
    lines.append("")

    ex = report.get("experiment_summary") or {}
    lines.append("## Experiment events")
    if ex.get("has_experiment_events"):
        lines.append(f"- trial_start: {ex.get('trial_start', 0)}")
        lines.append(f"- trial_end: {ex.get('trial_end', 0)}")
        lines.append(f"- block_start: {ex.get('block_start', 0)}")
        lines.append(f"- block_end: {ex.get('block_end', 0)}")
        lines.append(f"- trial_outcome: {ex.get('trial_outcome', 0)}")
    else:
        lines.append("- No trial/block/outcome events in log (loop-only run or task did not log experiment events).")
    lines.append("")

    tls = report.get("task_level_summary")
    if tls:
        lines.append("## Task-level summary (PsychoPy bridge)")
        lines.append(f"- **Trial starts:** {tls.get('trial_starts', 0)}")
        lines.append(f"- **Trial outcomes:** {tls.get('trial_outcomes', 0)}")
        lines.append(f"- **Block starts:** {tls.get('block_starts', 0)}")
        lines.append(f"- **Stimulus intended / realized:** {tls.get('stimulus_intended', 0)} / {tls.get('stimulus_realized', 0)}")
        ir = tls.get("intended_to_realized_mean_sec")
        lines.append(f"- **Intended→realized mean (s):** {ir if ir is not None else 'n/a'}")
        if tls.get("adaptive_param_logged"):
            lines.append(f"- **Adaptive param logged:** `{tls['adaptive_param_logged']}`")
        lines.append("")

    ad = report.get("adaptation") or {}
    lines.append("## Adaptation")
    lines.append(f"- control_signal events: {ad.get('control_signal', 0)}")
    lines.append(f"- adaptive_params_update: {ad.get('adaptive_params_update', 0)}")
    if ad.get("first_control_action"):
        lines.append(f"- first control action: `{ad['first_control_action']}`")
    lines.append("")

    ra = report.get("replay_agreement")
    lines.append("## Replay agreement")
    if ra:
        lines.append(f"- matches: {ra.get('matches')}")
        lines.append(f"- match_count / mismatch_count: {ra.get('match_count')} / {ra.get('mismatch_count')}")
        lines.append(f"- total_logged / total_replayed: {ra.get('total_logged')} / {ra.get('total_replayed')}")
        if ra.get("divergences_sample"):
            lines.append(f"- divergences (first {len(ra['divergences_sample'])}): see run_report.json for detail")
    else:
        lines.append("- No replay_result.json")
    lines.append("")

    bh = report.get("benchmark_highlights") or {}
    lines.append("## Benchmark highlights")
    lines.append(f"- window_count: {bh.get('window_count', 0)}")
    sp = bh.get("stage_p95_seconds") or {}
    if sp:
        lines.append("- Stage p95 (s): " + ", ".join(f"{k}={v:.4f}" for k, v in sp.items()))
    lines.append("")

    ds = report.get("diagnostics_summary") or {}
    lines.append("## Diagnostics")
    lines.append(f"- health: `{ds.get('health', 'n/a')}`")
    fb = ds.get("findings_by_level") or {}
    lines.append(f"- findings: critical={fb.get('critical', 0)}, warning={fb.get('warning', 0)}, info={fb.get('info', 0)}")
    lines.append("")

    lines.append("## Artifacts")
    for a in report.get("artifact_inventory") or []:
        st = "yes" if a.get("present") else "no"
        b = a.get("bytes")
        sz = f", {b} bytes" if b is not None else ""
        lines.append(f"- {a.get('name')}: present={st}{sz}")
    lines.append("")

    lines.append(f"## Config hash\n`{report.get('config_hash', '')}`\n")
    lines.append("See also **RUN_SUMMARY.md** for the compact run package summary.")
    return "\n".join(lines)


def write_run_report_artifacts(run_dir: Path | str) -> dict[str, Any]:
    """Build report and write run_report.json + run_report.md; refresh artifact rows for those files."""
    run_dir = Path(run_dir)
    report = build_run_report(run_dir)
    with open(run_dir / "run_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(run_dir / "run_report.md", "w", encoding="utf-8") as f:
        f.write(format_run_report_markdown(report))
    inv = list(report.get("artifact_inventory") or [])
    for name in ("run_report.json", "run_report.md"):
        p = run_dir / name
        for i, row in enumerate(inv):
            if row.get("name") == name:
                inv[i] = {"name": name, "present": True, "bytes": p.stat().st_size}
                break
    report["artifact_inventory"] = inv
    with open(run_dir / "run_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report
