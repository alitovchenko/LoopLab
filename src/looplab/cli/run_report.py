"""Emit the same human-readable output as `looplab report --run-dir <dir> --human`."""

from __future__ import annotations

import json
from pathlib import Path


def emit_human_run_report(run_dir: Path) -> None:
    """Print unified human run report for a completed run directory."""
    from looplab.benchmark.report import format_report_human, latency_report
    from looplab.benchmark.run_summary import build_run_package_summary, format_run_summary_markdown
    from looplab.logging.schema import LogEvent

    log_path = run_dir / "events.jsonl"
    if not log_path.exists():
        raise FileNotFoundError(f"events.jsonl not found under {run_dir}")

    events = []
    points = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = LogEvent.from_dict(json.loads(line))
            events.append(ev)
            if getattr(ev.event_type, "value", ev.event_type) == "benchmark_latency":
                points.append((ev.payload.get("label", "?"), ev.lsl_time))

    by_type: dict[str, int] = {}
    for e in events:
        t = getattr(e.event_type, "value", e.event_type)
        by_type[t] = by_type.get(t, 0) + 1

    bench = latency_report(points)
    report: dict = {
        "log_path": str(log_path),
        "event_counts": by_type,
        "n_events": len(events),
        "benchmark": bench,
    }
    session_file = run_dir / "session_summary.json"
    if session_file.exists():
        with open(session_file, encoding="utf-8") as f:
            report["session_summary"] = json.load(f)
    for name in ("replay_result.json", "config_snapshot.json"):
        p = run_dir / name
        if p.exists():
            report[name.replace(".json", "_path")] = str(p)

    report_warnings: list[str] = []
    if not points:
        report_warnings.append("no_benchmark_events")

    bench_for_diag = bench
    replay_for_summary = None
    bp = run_dir / "benchmark_summary.json"
    if bp.exists():
        with open(bp, encoding="utf-8") as f:
            bench_for_diag = json.load(f)
    rp = run_dir / "replay_result.json"
    if rp.exists():
        with open(rp, encoding="utf-8") as f:
            replay_for_summary = json.load(f)

    diag = None
    warning_inv = list(report_warnings)
    dp = run_dir / "diagnostics.json"
    if dp.exists():
        with open(dp, encoding="utf-8") as f:
            diag = json.load(f)
        for item in diag.get("findings", []):
            if item.get("level") in ("warning", "critical"):
                warning_inv.append(
                    f"{item['level']}: {item.get('code', '')} — {item.get('message', '')}"
                )

    run_package_summary = build_run_package_summary(
        report["event_counts"],
        bench_for_diag,
        run_dir=run_dir,
        session_summary=report.get("session_summary"),
        replay_result=replay_for_summary,
        warnings=warning_inv,
        diagnostics=diag,
    )

    lines = [
        f"Run report: {report['log_path']}",
        f"  Events: {report['n_events']} total",
        "  By type: " + ", ".join(f"{k}={v}" for k, v in sorted(report["event_counts"].items())),
        "",
        format_report_human(bench),
        "",
        format_run_summary_markdown(run_package_summary),
    ]
    print("\n".join(lines))
