#!/usr/bin/env python3
"""Export portable benchmark stats from a run dir (no huge by_label arrays)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from importlib.metadata import version as pkg_version
except ImportError:
    pkg_version = lambda _: "unknown"


def main() -> None:
    p = argparse.ArgumentParser(description="Export summary_stats.json from benchmark_summary.json")
    p.add_argument("run_dir", type=Path, help="Run directory with benchmark_summary.json")
    p.add_argument("--out", "-o", type=Path, help="Output path (default: stdout)")
    args = p.parse_args()
    bench_path = args.run_dir / "benchmark_summary.json"
    if not bench_path.exists():
        print(f"No {bench_path}", file=sys.stderr)
        sys.exit(1)
    d = json.loads(bench_path.read_text(encoding="utf-8"))
    by_label = d.get("by_label") or {}
    out = {
        "looplab_version": pkg_version("looplab"),
        "source_run_dir": str(args.run_dir.resolve()),
        "e2e_mean": d.get("e2e_mean"),
        "e2e_stats": d.get("e2e_stats"),
        "intended_to_realized_mean": d.get("intended_to_realized_mean"),
        "intended_to_realized_stats": d.get("intended_to_realized_stats"),
        "preprocess_latency_stats": d.get("preprocess_latency_stats"),
        "features_latency_stats": d.get("features_latency_stats"),
        "model_latency_stats": d.get("model_latency_stats"),
        "policy_latency_stats": d.get("policy_latency_stats"),
        "task_dispatch_latency_stats": d.get("task_dispatch_latency_stats"),
        "n_pull_chunk": len(by_label.get("pull_chunk", [])),
        "n_policy_done": len(by_label.get("policy_done", [])),
        "n_stimulus_intended": len(by_label.get("stimulus_intended", [])),
        "n_stimulus_realized": len(by_label.get("stimulus_realized", [])),
    }
    out = {k: v for k, v in out.items() if v is not None and v != []}
    text = json.dumps(out, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
