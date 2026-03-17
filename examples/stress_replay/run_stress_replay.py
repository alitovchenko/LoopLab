"""
Run replay with optional stressors (Workstream F): missing chunks, noise, drift, etc.

Usage (from repo root, with PYTHONPATH=src or pip install -e .):
  python examples/stress_replay/run_stress_replay.py --log path/to/events.jsonl --stream path/to/stream.jsonl
  python examples/stress_replay/run_stress_replay.py --log X --stream Y --drop-ratio 0.2 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay with optional stream/event stressors")
    parser.add_argument("--log", required=True, help="Event log JSONL path")
    parser.add_argument("--stream", required=True, help="Recorded stream JSONL path")
    parser.add_argument("--drop-ratio", type=float, default=0.0, help="Fraction of chunks to drop (0-1)")
    parser.add_argument("--noise-scale", type=float, default=0.0, help="Gaussian noise scale in time range (0 = off)")
    parser.add_argument("--noise-t-start", type=float, default=0.0)
    parser.add_argument("--noise-t-end", type=float, default=1e9)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    from looplab.replay.engine import ReplayEngine
    from looplab.replay.runner import ReplayRunner
    from looplab.replay.divergence import compute_divergence, format_divergence_report
    from looplab.replay.stream_recorder import StreamRecorder, load_recorded_chunks
    from looplab.replay.stressors import drop_chunks, add_noise
    from looplab.buffer.ring_buffer import RingBuffer
    from looplab.preprocess.pipeline import noop_preprocess
    from looplab.features.base import create_feature_extractor
    from looplab.model.base import create_model
    from looplab.controller.policy import create_policy

    log_path = Path(args.log)
    stream_path = Path(args.stream)
    if not log_path.exists():
        print(f"Log not found: {log_path}", file=sys.stderr)
        sys.exit(1)
    if not stream_path.exists():
        print(f"Stream not found: {stream_path}", file=sys.stderr)
        sys.exit(1)

    engine = ReplayEngine(str(log_path), str(stream_path))
    engine.load()
    chunks = load_recorded_chunks(stream_path)
    rng = np.random.default_rng(args.seed)

    if args.drop_ratio > 0:
        chunks = drop_chunks(chunks, args.drop_ratio, rng=rng)
        print(f"Dropped chunks: {len(chunks)} remaining", file=sys.stderr)
    if args.noise_scale > 0:
        chunks = add_noise(chunks, args.noise_scale, args.noise_t_start, args.noise_t_end, rng=rng)
        print("Noise applied", file=sys.stderr)

    out_stream = stream_path.parent / (stream_path.stem + "_stressed.jsonl")
    rec = StreamRecorder(out_stream)
    rec.open()
    for s, ts in chunks:
        rec.record(s, ts)
    rec.close()

    engine2 = ReplayEngine(str(log_path), str(out_stream))
    buffer = RingBuffer(500, 2)
    runner = ReplayRunner(
        engine2, buffer, noop_preprocess,
        create_feature_extractor("simple", {}), create_model("identity", {}), create_policy("identity", {}),
    )
    replayed = runner.run(seed=args.seed)
    logged = engine.get_control_sequence()
    report = compute_divergence(logged, replayed)
    print(format_divergence_report(report), file=sys.stderr)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
