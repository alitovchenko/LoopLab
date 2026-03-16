"""CLI: python -m looplab run|replay|benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="looplab", description="LoopLab closed-loop experiment SDK")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run experiment from config")
    run_p.add_argument("--config", "-c", required=True, help="Config file (YAML or JSON)")
    run_p.add_argument("--duration", "-d", type=float, default=60.0, help="Run duration in seconds (default 60)")
    run_p.add_argument("--tick-hz", type=float, default=10.0, help="Controller tick rate (default 10)")

    replay_p = sub.add_parser("replay", help="Replay session from log and recorded stream")
    replay_p.add_argument("--log", required=True, help="Event log JSONL path")
    replay_p.add_argument("--stream", help="Recorded stream path (optional)")
    replay_p.add_argument("--seed", type=int, default=42, help="Random seed for replay")

    bench_p = sub.add_parser("benchmark", help="Print benchmark report from log")
    bench_p.add_argument("--log", required=True, help="Event log JSONL path")

    args = parser.parse_args()

    if args.command == "run":
        from looplab.config.schema import load_config
        from looplab.runner import create_runner
        from looplab.streams.lsl_client import LSLInletClient
        from looplab.streams.clock import lsl_clock
        from looplab.replay.stream_recorder import StreamRecorder

        config = load_config(args.config)
        components = create_runner(config)
        loop = components["loop"]
        buffer = components["buffer"]
        writer = components["writer"]
        hooks = components.get("hooks")
        recorder = components.get("recorder")

        client = LSLInletClient(
            name=config.lsl.name,
            type_=config.lsl.type,
            source_id=config.lsl.source_id,
            chunk_size=config.lsl.chunk_size or 32,
            max_buffered=config.lsl.max_buffered,
            timeout=config.lsl.timeout,
        )
        client.connect()
        writer.open()

        if recorder:
            recorder.open()

        start = lsl_clock()
        tick_interval = 1.0 / args.tick_hz
        next_tick = start
        try:
            while lsl_clock() - start < args.duration:
                data, timestamps = client.pull_chunk(timeout=0.1, max_samples=256)
                if data.size > 0:
                    buffer.append(data, timestamps)
                    if hooks:
                        hooks.record_pull_chunk(lsl_clock())
                    if recorder and timestamps:
                        recorder.record(data, timestamps)
                now = lsl_clock()
                if now >= next_tick:
                    if hooks:
                        hooks.record_preprocess_done(now)
                    c = loop.tick()
                    if hooks and c:
                        hooks.record_policy_done(now)
                    next_tick = now + tick_interval
        finally:
            client.close()
            writer.close()
            if recorder:
                recorder.close()
        print("Run finished.", file=sys.stderr)

    elif args.command == "replay":
        from looplab.replay.engine import ReplayEngine
        from looplab.replay.runner import ReplayRunner
        from looplab.buffer.ring_buffer import RingBuffer
        from looplab.preprocess.pipeline import noop_preprocess
        from looplab.features.simple import SimpleFeatureExtractor
        from looplab.model.base import create_model
        from looplab.controller.policy import IdentityPolicy

        engine = ReplayEngine(args.log, args.stream)
        engine.load()
        events = engine.get_events()
        chunks = engine.get_chunks()
        if not chunks:
            print("No stream chunks to replay; only log loaded.", file=sys.stderr)
        else:
            n_samples, n_channels = chunks[0][0].shape[0], chunks[0][0].shape[1]
            buffer = RingBuffer(max_samples=n_samples * 10, n_channels=n_channels)
            model = create_model("identity", {})
            policy = IdentityPolicy()
            runner = ReplayRunner(
                engine,
                buffer,
                noop_preprocess,
                SimpleFeatureExtractor(),
                model,
                policy,
            )
            replayed = runner.run(seed=args.seed)
            logged = engine.get_control_sequence()
            print(f"Logged control signals: {len(logged)}", file=sys.stderr)
            print(f"Replayed control signals: {len(replayed)}", file=sys.stderr)
            if logged and replayed and len(logged) == len(replayed):
                match = all(
                    logged[i].get("action") == replayed[i].get("action")
                    for i in range(len(logged))
                )
                print(f"Determinism check: {'PASS' if match else 'FAIL'}", file=sys.stderr)

    elif args.command == "benchmark":
        from looplab.logging.schema import LogEvent
        from looplab.benchmark.report import latency_report, compute_latencies
        import json

        points = []
        with open(args.log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = LogEvent.from_dict(json.loads(line))
                if getattr(ev.event_type, "value", ev.event_type) == "benchmark_latency":
                    label = ev.payload.get("label", "?")
                    points.append((label, ev.lsl_time))
        report = latency_report(points)
        print(json.dumps(report, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
