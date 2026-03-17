"""
Run adaptive difficulty demo: pipeline drives task difficulty (easy/medium/hard), full artifact set.

Usage (from repo root or with PYTHONPATH=src):
  python examples/adaptive_difficulty_demo/run_demo.py --out-dir demo_out --duration 4
  python examples/adaptive_difficulty_demo/run_demo.py --out-dir demo_out --duration 4 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("numpy required: pip install -e .", file=sys.stderr)
    sys.exit(1)

# Synthetic clock before any looplab code that uses lsl_clock()
_t0_wall = time.monotonic()
_base_time = 1000.0


def _synthetic_clock() -> float:
    return _base_time + (time.monotonic() - _t0_wall)


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive difficulty demo: full artifact set")
    parser.add_argument("--out-dir", type=str, default="demo_out", help="Output directory for artifacts")
    parser.add_argument("--duration", type=float, default=4.0, help="Run duration in seconds")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for replay")
    args = parser.parse_args()

    from looplab.streams import clock as clock_mod
    clock_mod.set_clock(_synthetic_clock)

    demo_dir = Path(__file__).resolve().parent
    # Register demo plugins before loading config / create_runner
    import importlib.util
    spec = importlib.util.spec_from_file_location("plugins", demo_dir / "plugins.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["plugins"] = mod
    spec.loader.exec_module(mod)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "events.jsonl"
    stream_path = out_dir / "stream.jsonl"

    from looplab.config.schema import load_config, config_to_dict
    config = load_config(demo_dir / "config.yaml")
    config.log_path = str(log_path)
    config.record_stream_path = str(stream_path)

    with open(out_dir / "config_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(config_to_dict(config), f, indent=2)

    from looplab.runner import create_runner
    from looplab.controller.loop import ControllerLoop
    components = create_runner(config)
    loop = ControllerLoop(
        buffer=components["buffer"],
        preprocess=components["preprocess"],
        feature_extractor=components["feature_extractor"],
        model=components["model"],
        policy=components["policy"],
        adapter=components["adapter"],
        logger=components["logger"],
        min_samples=8,
    )
    buffer = components["buffer"]
    writer = components["writer"]
    hooks = components.get("hooks")
    if hooks:
        loop.set_hooks(hooks)
    recorder = components.get("recorder")

    writer.open()
    if recorder:
        recorder.open()

    lsl_clock = clock_mod.lsl_clock
    start = lsl_clock()
    duration = args.duration
    chunk_interval = 0.02
    n_channels = config.buffer.n_channels
    chunk_size = config.lsl.chunk_size or 8
    srate = 50.0
    rng = np.random.default_rng(args.seed)
    sample_idx = 0

    try:
        while lsl_clock() - start < duration:
            data = rng.standard_normal((chunk_size, n_channels)).astype(np.float64)
            ts_start = start + sample_idx / srate
            timestamps = [ts_start + j / srate for j in range(chunk_size)]
            sample_idx += chunk_size
            buffer.append(data, timestamps)
            if hooks:
                hooks.record_pull_chunk(lsl_clock())
            if recorder:
                recorder.record(data, timestamps)
            loop.tick()
            time.sleep(chunk_interval)
    finally:
        writer.close()
        if recorder:
            recorder.close()

    print("Adaptive difficulty demo: session recorded. Post-processing...", file=sys.stderr)

    # Replay with same config (same model/policy)
    from looplab.replay.engine import ReplayEngine
    from looplab.replay.runner import ReplayRunner
    from looplab.replay.divergence import compute_divergence
    from looplab.buffer.ring_buffer import RingBuffer
    from looplab.preprocess.pipeline import noop_preprocess
    from looplab.features.base import create_feature_extractor
    from looplab.model.base import create_model
    from looplab.controller.policy import create_policy

    engine = ReplayEngine(str(log_path), str(stream_path))
    engine.load()
    chunks = engine.get_chunks()
    logged = engine.get_control_sequence()
    if not chunks:
        replay_result = {
            "match_count": 0,
            "mismatch_count": len(logged),
            "total_logged": len(logged),
            "total_replayed": 0,
            "matches": False,
            "divergences": [],
        }
    else:
        r_buffer = RingBuffer(max_samples=config.buffer.max_samples, n_channels=config.buffer.n_channels)
        runner = ReplayRunner(
            engine, r_buffer, noop_preprocess,
            create_feature_extractor(config.feature_extractor, config.feature_extractor_config),
            create_model(config.model, config.model_config),
            create_policy(config.policy, config.policy_config),
        )
        replayed = runner.run(seed=args.seed)
        replay_result = compute_divergence(logged, replayed)
    with open(out_dir / "replay_result.json", "w", encoding="utf-8") as f:
        json.dump(replay_result, f, indent=2)

    # Benchmark
    from looplab.logging.schema import LogEvent
    from looplab.benchmark.report import latency_report
    points = []
    event_counts = {}
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = LogEvent.from_dict(json.loads(line))
            t = getattr(ev.event_type, "value", ev.event_type)
            event_counts[t] = event_counts.get(t, 0) + 1
            if t == "benchmark_latency":
                points.append((ev.payload.get("label", "?"), ev.lsl_time))
    bench_report = latency_report(points)
    with open(out_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(bench_report, f, indent=2)

    artifacts_ok = log_path.exists() and log_path.stat().st_size > 0
    artifacts_ok = artifacts_ok and stream_path.exists() and stream_path.stat().st_size > 0
    replay_ok = replay_result.get("matches", False) if chunks else True
    session_summary = {
        "duration_sec": duration,
        "seed": args.seed,
        "out_dir": str(out_dir),
        "artifacts_ok": artifacts_ok,
        "replay_ok": replay_ok,
        "lsl_available": False,
        "backend": "synthetic",
        "paradigm": "adaptive_difficulty",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    with open(out_dir / "session_summary.json", "w", encoding="utf-8") as f:
        json.dump(session_summary, f, indent=2)

    run_warnings = []
    if not points:
        run_warnings.append("no_benchmark_events")
    if not chunks:
        run_warnings.append("replay_skipped_no_chunks")
    from looplab.benchmark.run_summary import build_run_package_summary, format_run_summary_markdown
    config_snap = json.loads((out_dir / "config_snapshot.json").read_text(encoding="utf-8"))
    run_package_summary = build_run_package_summary(
        event_counts,
        bench_report,
        run_dir=out_dir,
        session_summary=session_summary,
        replay_result=replay_result,
        config_snapshot=config_snap,
        backend="synthetic",
        warnings=run_warnings,
    )
    with open(out_dir / "run_package_summary.json", "w", encoding="utf-8") as f:
        json.dump(run_package_summary, f, indent=2)
    with open(out_dir / "RUN_SUMMARY.md", "w", encoding="utf-8") as f:
        f.write(format_run_summary_markdown(run_package_summary))

    print(f"Artifacts written to {out_dir}/", file=sys.stderr)
    print("  config_snapshot.json, events.jsonl, stream.jsonl, replay_result.json,", file=sys.stderr)
    print("  benchmark_summary.json, session_summary.json, run_package_summary.json, RUN_SUMMARY.md", file=sys.stderr)


if __name__ == "__main__":
    main()
